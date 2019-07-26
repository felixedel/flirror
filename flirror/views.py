import abc

from flask import current_app, render_template
from flask.views import MethodView
from pony.orm import db_session, desc, select

from flirror.database import CalendarEvent, Weather


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
        city = settings.get("city")

        # Get weather data from database
        weather, forecasts = self.get_weather(city)

        # Provide weather data in template context
        context = self.get_context(weather=weather, forecasts=forecasts)
        return render_template(self.template_name, **context)

    @db_session
    def get_weather(self, city):
        # TODO Get the latest weather entry based on what?
        # TODO Do we need to check the city at all? There should be only one
        #  data-crawler per mirror ensuring that the correct data is crawled and
        #  stored in the database.
        for weather in select(w for w in Weather if w.city == city).order_by(
            desc(Weather.date)
        ):
            # TODO Simply return the first weather we found
            # NOTE Directly return the full list of forecasts, because it needs
            # and active db_session to get it.
            return weather, list(weather.forecasts)


class CalendarView(FlirrorMethodView):

    endpoint = "calendar"
    rule = "/calendar"
    template_name = "calendar.html"

    def get(self):
        # Get view-specific settings from config
        # TODO Do we need to filter for these calendars?
        #  settings = current_app.config["MODULES"].get(self.endpoint)
        #  calendars = settings["calendars"]

        events = self.get_events()
        # Provide events in template context
        context = self.get_context(events=events)
        return render_template(self.template_name, **context)

    @db_session
    def get_events(self):
        # Get events from database
        events = []
        # TODO How to limit the amount of items to retrieve from the database?
        #  Use the max_items setting here also?
        for event in select(e for e in CalendarEvent).order_by(
                CalendarEvent.start
        ):
            events.append(event)
        return events


class MapView(FlirrorMethodView):

    endpoint = "map"
    rule = "/map"
    template_name = "map.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        context = self.get_context(**settings)
        return render_template(self.template_name, **context)
