import abc

import requests
from flask import current_app, render_template, url_for
from flask.views import MethodView


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

        # Here we have place for overall meta data (like flirror version or so)
        all_data = {"modules": {}}

        for module_id, module_config in current_app.config.get("MODULES", {}).items():
            module_type = module_config.get("type")
            # TODO Error handling for wrong/missing keys

            res = requests.get(url_for(f"api-{module_type}", _external=True))
            # TODO Error handling?
            # Add the error message as module data, so it could be displayed with
            # a general module-error template that can be included in the module.html
            # in case this error field is set.
            data = res.json()

            all_data["modules"][module_id] = {
                "type": module_type,
                "data": data,
            }

        # TODO dummy data for map tile
        all_data["modules"]["map"] = {
            "data": current_app.config["MODULES"].get("map"),
            "type": "map",
        }
        all_data["modules"]["map"]["data"]["_timestamp"] = 12345.0

        print(all_data)
        context = self.get_context(**all_data)
        return render_template(self.template_name, **context)


class WeatherView(FlirrorMethodView):

    endpoint = "weather"
    rule = "/weather"
    template_name = "weather.html"

    FLIRROR_OBJECT_KEY = "module_weather"

    def get(self):
        # TODO Get view-specific settings from config
        # settings = current_app.config["MODULES"].get(self.endpoint)
        # city = settings.get("city")

        res = requests.get(url_for("api-weather", _external=True))
        # TODO Error handling?
        weather = res.json()

        # Provide weather data in template context
        context = self.get_context(weather=weather)
        return render_template(self.template_name, **context)


class CalendarView(FlirrorMethodView):

    endpoint = "calendar"
    rule = "/calendar"
    template_name = "calendar.html"

    def get(self):
        # Get view-specific settings from config
        # TODO Do we need to filter for these calendars?
        #  settings = current_app.config["MODULES"].get(self.endpoint)
        #  calendars = settings["calendars"]

        res = requests.get(url_for("api-calendar", _external=True))
        # TODO Error handling?
        data = res.json()

        # Provide events in template context
        context = self.get_context(**data)
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
