import abc

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

    # TODO Change to template filter registered by the weather module
    weather_icons = {
        "01d": "wi wi-day-sunny",
        "02d": "wi wi-day-cloudy",
        "03d": "wi wi-cloud",
        "04d": "wi wi-cloudy",
        "09d": "wi wi-day-showers",
        "10d": "wi wi-day-rain",
        "11d": "wi wi-day-thunderstorm",
        "13d": "wi wi-day-snow",
        "50d": "wi wi-dust",
        "01n": "wi wi-night-clear",
        "02n": "wi-night-alt-cloudy",
        "03n": "wi wi-cloud",
        "04n": "wi wi-cloudy",
        "09n": "wi wi-night-showers-rain",
        "10n": "wi wi-night-rain",
        "11n": "wi wi-night-thunderstorm",
        "13n": "wi wi-night-snow",
        "50n": "wi wi-dust",
    }

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        weather_data = self.get_weather(settings)
        context = self.get_context(**weather_data)
        return render_template(self.template_name, **context)

    def get_weather(self, settings):
        api_key = settings.get("api_key")
        language = settings.get("language")
        city = settings.get("city")
        temp_unit = settings.get("temp_unit")

        # Create OWM client
        owm = OWM(API_key=api_key, language=language, version="2.5")
        obs = owm.weather_at_place(city)

        # Get today's weather and weekly forecast
        weather = obs.get_weather()
        fc = owm.daily_forecast(city, limit=7)

        fc_data = []
        # Skip the first element as we already have the weather for today
        for fc_weather in list(fc.get_forecast())[1:]:
            fc_data.append(self._parse_weather_data(fc_weather, temp_unit))

        weather_data = self._parse_weather_data(weather, temp_unit)

        return {"city": city, "weather": weather_data, "forecast": fc_data}

    def _parse_weather_data(self, weather, temp_unit):
        return {
            "date": weather.get_reference_time(timeformat="date"),
            "temperature": weather.get_temperature(unit=temp_unit),
            "status": weather.get_status(),
            "detailed_status": weather.get_detailed_status(),
            "sunrise_time": weather.get_sunrise_time("iso"),
            "sunset_time": weather.get_sunset_time("iso"),
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon_cls": self.weather_icons.get(weather.get_weather_icon_name()),
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
