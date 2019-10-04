import abc
from datetime import datetime

from flask import current_app, render_template
from flask.views import MethodView

from flirror.database import get_object_by_key


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

    FLIRROR_OBJECT_KEY = "module_weather"

    def get(self):
        # TODO Get view-specific settings from config
        # settings = current_app.config["MODULES"].get(self.endpoint)
        # city = settings.get("city")

        # Get weather data from database
        weather = self.get_weather()

        weather["_timestamp"] = datetime.utcfromtimestamp(weather["_timestamp"])

        # Provide weather data in template context
        context = self.get_context(weather=weather)
        return render_template(self.template_name, **context)

    def get_weather(self):
        db = current_app.extensions["database"]
        weather = get_object_by_key(db, self.FLIRROR_OBJECT_KEY)
        # Change timestamps to datetime objects
        # TODO This should be done before storing the data, but I'm not sure
        # how to tell Pony how to serialize the datetime to JSON
        weather["date"] = datetime.utcfromtimestamp(weather["date"])
        for fc in weather["forecasts"]:
            fc["date"] = datetime.utcfromtimestamp(fc["date"])
        return weather


class CalendarView(FlirrorMethodView):

    endpoint = "calendar"
    rule = "/calendar"
    template_name = "calendar.html"

    FLIRROR_OBJECT_KEY = "module_calendar"

    def get(self):
        # Get view-specific settings from config
        # TODO Do we need to filter for these calendars?
        #  settings = current_app.config["MODULES"].get(self.endpoint)
        #  calendars = settings["calendars"]

        data = self.get_events()
        # Provide events in template context
        context = self.get_context(**data)
        return render_template(self.template_name, **context)

    def get_events(self):
        db = current_app.extensions["database"]
        data = get_object_by_key(db, self.FLIRROR_OBJECT_KEY)
        # Change timestamps to datetime objects
        # TODO This should be done before storing the data, but I'm not sure
        # how to tell Pony how to serialize the datetime to JSON
        for event in data["events"]:
            event["start"] = datetime.utcfromtimestamp(event["start"])
            event["end"] = datetime.utcfromtimestamp(event["end"])

        data["_timestamp"] = datetime.utcfromtimestamp(data["_timestamp"])
        return data


class MapView(FlirrorMethodView):

    endpoint = "map"
    rule = "/map"
    template_name = "map.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        context = self.get_context(**settings)
        return render_template(self.template_name, **context)
