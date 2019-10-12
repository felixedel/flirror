from flask import Flask

from .api import CalendarApi, NewsfeedApi, StocksApi, WeatherApi
from .database import create_database_and_entities
from .helpers import make_error_handler
from .utils import format_time, list_filter, prettydate, weather_icon
from .views import CalendarView, IndexView, MapView, WeatherView

FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"


def create_app():
    app = Flask(__name__)
    app.config.from_envvar(FLIRROR_SETTINGS_ENV)

    app.secret_key = app.config["SECRET_KEY"]

    # The central index page showing all tiles
    IndexView.register_url(app)

    # The modules API
    WeatherApi.register_url(app)
    CalendarApi.register_url(app)
    NewsfeedApi.register_url(app)
    StocksApi.register_url(app)

    # The module views (only necessary for debug mode?)
    WeatherView.register_url(app)
    CalendarView.register_url(app)
    MapView.register_url(app)

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
