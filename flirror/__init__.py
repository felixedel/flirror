import logging
import subprocess
from typing import Any, Dict, Optional, Union

import click
from flask import (
    abort,
    Flask,
    jsonify,
    make_response,
    render_template,
    request,
    Response,
)
from flask_assets import Bundle, Environment

from .database import (
    create_database_and_entities,
    get_object_by_key,
    store_object_by_key,
)
from .exceptions import ModuleDataException
from .helpers import make_error_handler
from .modules import FlirrorModule
from .modules.calendar import calendar_module
from .modules.clock import clock_module
from .modules.newsfeed import newsfeed_module
from .modules.stocks import stocks_module
from .modules.weather import weather_module
from .utils import (
    clean_string,
    discover_flirror_modules,
    discover_plugins,
    format_time,
    prettydate,
)
from .views import IndexView

FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"
DEFAULT_OBJECT_KEY = "data"

LOGGER = logging.getLogger(__name__)


class Flirror(Flask):
    @property
    def modules(self):
        """
        For convenience, so we don't have to access the blueprints attribute
        when dealing with modules.
        """
        return self.blueprints

    def register_module(self, module: FlirrorModule, **options: Any) -> None:
        LOGGER.info("Register module '%s'", module.name)
        # Always prefix the module's endpoints with its name
        url_prefix = f"/{module.name}"
        self.register_blueprint(module, url_prefix=url_prefix, **options)

        # TODO (felix): If we want to register something beyond Flask's
        # blueprint capabilities, we could add a back-reference to the app in
        # the module class and call something like:
        # blueprint.register(self, options, first_registration)
        # https://github.com/pallets/flask/blob/master/src/flask/blueprints.py#L233

    def basic_get(
        self, template_name: str, object_key: Optional[str] = None
    ) -> Response:
        module_id = request.args.get("module_id")
        if not module_id:
            return self.json_abort(400, "Parameter 'module_id' is missing")
        try:
            template = self.get_module_template(module_id, template_name, object_key)
            return jsonify({"_template": template})
        except ModuleDataException as e:
            return self.json_abort(400, str(e))

    def store_module_data(
        self, module_id: str, data: Dict[str, Any], object_key: Optional[str] = None
    ) -> None:
        # Use "data" as default object key
        if object_key is None:
            object_key = DEFAULT_OBJECT_KEY

        module_object_key = f"module.{module_id}.{object_key}"
        store_object_by_key(self.extensions["database"], module_object_key, data)

    def get_module_data(
        self, module_id: str, object_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the data for a specific module.
        This method can be used by both, views and other arbitrary code parts to
        retrieve the data for the module specified by the function arguments.
        """

        # Use "data" as default object key
        if object_key is None:
            object_key = DEFAULT_OBJECT_KEY

        module_object_key = f"module.{module_id}.{object_key}"
        return get_object_by_key(self.extensions["database"], module_object_key)

    def get_module_template(
        self, module_id: str, template_name: str, object_key: Optional[str] = None
    ) -> str:
        data = self.get_module_data(module_id, object_key)
        context = self.get_template_context(module_id, data)

        return render_template(template_name, **context)

    def get_template_context(
        self, module_id: str, data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # Get view specifc settings from config
        module_configs = [
            m for m in self.config.get("MODULES", {}) if m.get("id") == module_id
        ]

        if module_configs:
            module_config = module_configs[0]
        else:
            # TODO template/raw output?
            raise ModuleDataException(
                f"Could not find any module config for ID '{module_id}'. "
                "Are you sure this one is specified in the config file?"
            )

        # Change timestamps to datetime objects
        # TODO This should be done before storing the data, but I'm not sure
        # how to tell Pony how to serialize the datetime to JSON

        error = None
        if data is None:
            error = {
                # TODO Which error code should we use here?
                "code": 400,
                "msg": (
                    f"Could not find any data for module with ID '{module_id}'. "
                    "Did the appropriate crawler run?"
                ),
            }

        # Build template context and return template via JSON
        context = {
            "module": {
                # TODO (felix): Remove this fallback in a later future version
                "name": module_config.get("module") or module_config.get("type"),
                "id": module_id,
                "config": module_config["config"],
                "display": module_config["display"],
                "error": error,
                "data": data,
            }
        }
        return context

    def json_abort(self, status: int, msg: Optional[str] = None) -> Response:
        response: Dict[str, Union[str, int]] = {"error": status}
        if msg is not None:
            response["msg"] = msg
        return abort(make_response(jsonify(response), status))

    def register_plugins(self) -> None:
        plugins = discover_plugins()
        flirror_modules = discover_flirror_modules(plugins)
        for fm in flirror_modules:
            self.register_module(fm)


def create_app(
    config: Optional[Dict] = None, jinja_options: Optional[Any] = None
) -> Flirror:
    """
    Load configuration file and initialize flirror app with necessary
    components like database and modules.
    """

    # TODO (felix): Find a better way to overwrite the jinja_options for the unit tests.
    # As stated in https://github.com/pallets/flask/blob/38eb5d3b49d628785a470e2e773fc5ac82e3c8e4/src/flask/app.py#L679
    # overwriting the jinja_options should be done as early as possible.
    app = Flirror(__name__)

    # Overwrite or set additional jinja_options. This is currently only used for
    # validating the templates in the unit tests.
    if jinja_options is not None:
        app.jinja_options = {**app.jinja_options, **jinja_options}

    # Load the config from the python file specified in the env vars and
    # overwrite values that are provided directly via arguments.
    # TODO (felix): Add default settings, once we have some
    # TODO (felix): Validate config?
    app.config.from_envvar(FLIRROR_SETTINGS_ENV)
    if config is not None:
        app.config.from_mapping(config)

    app.secret_key = app.config["SECRET_KEY"]

    # Using the URL prefix is a good way so modules cannot conflict with each other
    # TODO (felix): Auto look-up for modules by name and modules specified in the
    # config file or something like
    # https://packaging.python.org/guides/creating-and-discovering-plugins/
    # TODO (felix): Prefix each module's URL with its name to avoid name clashes
    # between modules and all can simply use the same url_rule ("/").
    # Register all standard modules
    for module in [
        clock_module,
        weather_module,
        calendar_module,
        newsfeed_module,
        stocks_module,
    ]:
        app.register_module(module)

    # Discover and register custom plugins
    app.register_plugins()

    # Connect to the sqlite database
    # TODO (felix): Maybe we could drop the 'create_db' here?
    # Usually, it should be sufficient, when the crawler creates the database. If it
    # is not created here, we should just provide some message to start the crawler.
    db = create_database_and_entities(
        provider="sqlite", filename=app.config["DATABASE_FILE"], create_db=True
    )

    # Store the dabase connection in flask's extensions dictionary.
    if not hasattr(app, "extensions"):
        app.extensions = {}
    if "database" not in app.extensions:
        app.extensions["database"] = db

    return app


def create_web(
    config: Optional[Dict] = None, jinja_options: Optional[Any] = None
) -> Flirror:
    """
    Load the configuration file and initialize the flirror app with basic
    components plus everything that's necessary for the web app like jinja2
    env, template filters and assets (SCSS/CSS).
    """

    app = create_app(config, jinja_options)

    # The central index page showing all tiles
    IndexView.register_url(app)

    # Register error handler to known status codes
    error_handler = make_error_handler()
    app.register_error_handler(400, error_handler)
    app.register_error_handler(403, error_handler)
    app.register_error_handler(404, error_handler)

    # Add custom Jinja2 template filters
    app.add_template_filter(prettydate)
    app.add_template_filter(format_time)
    app.add_template_filter(clean_string)

    # Initialize webassets to work with SCSS files
    assets = Environment(app)
    scss = Bundle("scss/all.scss", filters="pyscss", output="all.css")
    assets.register("scss_all", scss)

    return app


# NOTE (felix): It looks like poetry only supports python entry points and no
# arbitrary scripts (e.g. shell) like setup.py (although a setup.py file is
# generated in the end): https://github.com/python-poetry/poetry/issues/241
# Thus, we start gunicorn as subprocess from within Python to bypass this
# limitation.
@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("gunicorn_options", nargs=-1, type=click.UNPROCESSED)
def run_web(gunicorn_options: Dict):
    # Start gunicorn to serve the flirror application
    cmd = ["gunicorn", "flirror:create_web()"]

    # Allow arbitrary gunicorn options to be provided
    if gunicorn_options is not None:
        cmd.extend(gunicorn_options)

    subprocess.call(cmd)
