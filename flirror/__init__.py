from flask import Flask

from .google_auth import OAuth2View, OAuth2CallbackView
from .views import CalendarView, IndexView, MapView, WeatherView

FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"


def create_app():
    app = Flask(__name__)
    app.config.from_envvar(FLIRROR_SETTINGS_ENV)

    app.secret_key = app.config["SECRET_KEY"]

    # The central index page showing all tiles
    IndexView.register_url(app)

    # The modules
    WeatherView.register_url(app)
    CalendarView.register_url(app)
    MapView.register_url(app)

    # OAuth 2.0 authentication for Google APIs
    OAuth2View.register_url(app)
    OAuth2CallbackView.register_url(app)

    return app


app = create_app()
