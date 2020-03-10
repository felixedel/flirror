import logging
import subprocess

import click
from flask import Flask
from flask_assets import Bundle, Environment

from .database import create_database_and_entities
from .exceptions import FlirrorConfigError
from .helpers import make_error_handler
from .modules.weather import weather_module
from .utils import clean_string, format_time, list_filter, prettydate, weather_icon
from .views import CalendarApi, IndexView, NewsfeedApi, StocksApi

FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"

LOGGER = logging.getLogger(__name__)


class Flirror(Flask):

    crawlers = {}

    def register_module(self, module, **options):
        LOGGER.info("Register module %s", module.name)
        self.register_blueprint(module, **options)
        self.register_crawler(module)

    def register_crawler(self, module):
        LOGGER.debug(
            "Register crawler %s for module '%s'", module._crawler, module.name
        )
        if (
            module.name in self.crawlers
            and self.crawlers[module.name] is not module._crawler
        ):
            raise FlirrorConfigError(
                f"A different module with the specified name '{module.name}' was "
                "already loaded."
            )
        self.crawlers[module.name] = module._crawler

        # TODO (felix): Should we add a back-reference to the app in the
        # crawler, like:
        # blueprint.register(self, options, first_registration)


def create_app(config=None, jinja_options=None):
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
    # config file.
    # TODO (felix): Prefix each module's URL with its name to avoid name clashes
    # between modules and all can simply use the same url_rule ("/").
    app.register_module(weather_module, url_prefix="/weather")

    # Connect to the sqlite database
    # TODO (felix): Maybe we could drop the 'create_db' here?
    # Usually, it should be sufficient, when the crawler creates the database. If it
    # is not created here, we should just provide somee message to start the crawler.
    db = create_database_and_entities(
        provider="sqlite", filename=app.config["DATABASE_FILE"], create_db=True
    )

    # Store the dabase connection in flask's extensions dictionary.
    # TODO (felix): Is there a better place to store it?
    if not hasattr(app, "extensions"):
        app.extensions = {}
    if "database" not in app.extensions:
        app.extensions["database"] = db

    return app


def create_web(config=None, jinja_options=None):
    """
    Load the configuration file and initialize the flirror app with basic
    components plus everything that's necessary for the web app like jinja2
    env, template filters and assets (SCSS/CSS).
    """

    app = create_app(config, jinja_options)

    # The central index page showing all tiles
    IndexView.register_url(app)

    # The modules API
    CalendarApi.register_url(app)
    NewsfeedApi.register_url(app)
    StocksApi.register_url(app)

    # Register error handler to known status codes
    error_handler = make_error_handler()
    app.register_error_handler(400, error_handler)
    app.register_error_handler(403, error_handler)
    app.register_error_handler(404, error_handler)

    # Add custom Jinja2 template filters
    app.add_template_filter(weather_icon)
    app.add_template_filter(prettydate)
    app.add_template_filter(format_time)
    app.add_template_filter(list_filter)
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
def run_web(gunicorn_options):
    # Start gunicorn to serve the flirror application
    cmd = ["gunicorn", "flirror:create_web()"]

    # Allow arbitrary gunicorn options to be provided
    if gunicorn_options is not None:
        cmd.extend(gunicorn_options)

    subprocess.call(cmd)
