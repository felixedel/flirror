from flask import Flask

from .views import CalendarView, IndexView, MapView, WeatherView

FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"


def create_app():
    app = Flask(__name__)
    app.config.from_envvar(FLIRROR_SETTINGS_ENV)

    IndexView.register_url(app)
    WeatherView.register_url(app)
    CalendarView.register_url(app)
    MapView.register_url(app)

    return app


app = create_app()
