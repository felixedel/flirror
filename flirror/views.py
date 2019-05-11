import abc
import functools
from datetime import datetime

from flask import current_app, render_template
from flask.views import MethodView
from pyowm import OWM


class FlirrorMethodView(MethodView):
    @property
    @abc.abstractmethod
    def endpoint(self):
        pass

    @property
    @abc.abstractmethod
    def rule(self):
        pass

    @property
    @abc.abstractmethod
    def template_name(self):
        pass

    @classmethod
    def register_url(cls, app, **options):
        app.add_url_rule(cls.rule, view_func=cls.as_view(cls.endpoint), **options)

    def get_context(self, **kwargs):
        # Initialize context with meta fields that should be available on all pages
        # E.g. the flirror version or something like this
        context = {}

        # Add additionally provided kwargs
        context = {**context, **kwargs}
        return context


class IndexView(FlirrorMethodView):

    endpoint = "index"
    rule = "/"
    template_name = "index.html"

    def get(self):
        context = self.get_context(**current_app.config["MODULES"])
        return render_template(self.template_name, **context)


class WeatherView(FlirrorMethodView):

    endpoint = "weather"
    rule = "/weather"
    template_name = "weather.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        weather_data = self.get_weather(settings)
        context = self.get_context(**weather_data)
        return render_template(self.template_name, **context)

    def get_weather(self, settings):
        api_key = settings.get("api_key")
        language = settings.get("language")
        town = settings.get("town")
        temp_unit = settings.get("temp_unit")

        owm = OWM(API_key=api_key, language=language, version="2.5")
        obs = owm.weather_at_place(town)
        weather = obs.get_weather()

        fc = owm.daily_forecast(town, limit=6)

        fc_data = []
        for fc_weather in fc.get_forecast():
            fc_data.append({
                "date": fc_weather.get_reference_time(timeformat="date"),
                "temperature": fc_weather.get_temperature(unit=temp_unit),
                "status": fc_weather.get_status(),
            })

        return {
            "town": town,
            "date": weather.get_reference_time(timeformat="date"),
            "temperature": weather.get_temperature(unit=temp_unit),
            "status": weather.get_status(),
            "detailed_status": weather.get_detailed_status(),
            "sunrise_time": weather.get_sunrise_time("iso"),
            "sunset_time": weather.get_sunset_time("iso"),
            "forecast": fc_data,
        }


class CalendarView(FlirrorMethodView):

    endpoint = "calendar"
    rule = "/calendar"
    template_name = "calendar.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        context = self.get_context(**settings)
        return render_template(self.template_name, **context)


class MapView(FlirrorMethodView):

    endpoint = "map"
    rule = "/map"
    template_name = "map.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        context = self.get_context(**settings)
        return render_template(self.template_name, **context)
