import abc
from datetime import datetime

from flask import current_app, render_template
from flask.views import MethodView
from pony.orm import db_session, desc, select

from flirror.database import Weather


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
    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        weather, forecasts = self.get_weather(settings)
        context = self.get_context(weather=weather, forecasts=forecasts)
        return render_template(self.template_name, **context)

    @db_session
    def get_weather(self, settings):
        # TODO Use the city as where clause in the SQL statement
        city = settings.get("city")

        for weather in select(w for w in Weather if w.city == city).order_by(
            desc(Weather.date)
        ):
            print(weather.city)
            # TODO Simply return the first weather we found
            # NOTE Directly return the full list of forecasts, because it needs
            # and active db_session to get it.
            return weather, list(weather.forecasts)


class CalendarView(FlirrorMethodView):

    endpoint = "calendar"
    rule = "/calendar"
    template_name = "calendar.html"

    api_scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
    api_service_name = "calendar"
    api_version = "v3"

    default_max_items = 5

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        calendars = settings["calendars"]
        max_items = settings.get("max_items", self.default_max_items)

        cred = self.get_credentials()


        events, events_json = self.get_events(service, calendars, max_items)
        context = self.get_context(events=events, events_json=events_json)
        return render_template(self.template_name, **context)

    def get_events(self, api_service, calendars, max_items):
        all_events = []
        # Use the value from config
        calendar_list = api_service.calendarList().list().execute()
        calendar_items = calendar_list.get("items")
        current_app.logger.info("%s", cals_filtered)

        for cal_item in cals_filtered:
            # Call the calendar API
            now = "{}Z".format(datetime.utcnow().isoformat())  # 'Z' indicates UTC time
            current_app.logger.info("Getting the upcoming 10 events")
            events_result = (
                api_service.events()
                .list(
                    calendarId=cal_item["id"],
                    timeMin=now,
                    maxResults=max_items,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            all_events.extend(self._parse_event_data(event) for event in events)

        # Sort the events from multiple calendars, but ignore the timezone
        all_events = sorted(all_events, key=lambda k: k["start"].replace(tzinfo=None))
        return all_events[:max_items], events



class MapView(FlirrorMethodView):

    endpoint = "map"
    rule = "/map"
    template_name = "map.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        context = self.get_context(**settings)
        return render_template(self.template_name, **context)
