from flask import Flask
from flask_assets import Bundle, Environment

from .database import create_database_and_entities
from .helpers import make_error_handler
from .utils import clean_string, format_time, list_filter, prettydate, weather_icon
from .views import CalendarApi, IndexView, NewsfeedApi, StocksApi, WeatherApi

FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"


def create_app(config=None, jinja_options=None):
    # TODO (felix): Find a better way to overwrite the jinja_options for the unit tests.
    # As stated in https://github.com/pallets/flask/blob/38eb5d3b49d628785a470e2e773fc5ac82e3c8e4/src/flask/app.py#L679
    # overwriting the jinja_options should be done as early as possible.
    app = Flask(__name__)

    # Overwrite or set additional jinja_options. This is currently only used for
    # validating the templates in the unit tests.
    if jinja_options is not None:
        app.jinja_options = {**app.jinja_options, **jinja_options}

    # Load the config from the python file specified in the env vars and
    # overwrite values that are provided directly via arguments.
    app.config.from_envvar(FLIRROR_SETTINGS_ENV)
    if config is not None:
        app.config.from_mapping(config)

    app.secret_key = app.config["SECRET_KEY"]

    # The central index page showing all tiles
    IndexView.register_url(app)

    # The modules API
    WeatherApi.register_url(app)
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

    # Connect to the sqlite database
    # TODO (felix): Maybe we could drop the 'create_db' here?
    # Usually, it should be sufficient, when the crawler creates the database. If it
    # is not created here, we should just provide somee message to start the crawler.
    db = create_database_and_entities(
        provider="sqlite", filename=app.config["DATABASE_FILE"], create_db=True,
    )

    # Store the dabase connection in flask's extensions dictionary.
    # TODO (felix): Is there a better place to store it?
    if not hasattr(app, "extensions"):
        app.extensions = {}
    if "database" not in app.extensions:
        app.extensions["database"] = db

    return app
