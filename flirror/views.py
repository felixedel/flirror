import abc
from datetime import datetime

import flask
import google.oauth2.credentials
import googleapiclient.discovery
from dateutil.parser import parse as dtparse
from flask import abort, current_app, render_template
from flask.views import MethodView
from pony.orm import db_session, desc, select

from flirror.database import Oauth2Credentials, Weather, WeatherForecast


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

    # TODO Maybe we could use this also as a fallback if no calendar from the list matched
    default_calendars = ["primary"]
    default_max_items = 5

    @db_session
    def get_credentials(self):
        for credentials in select(c for c in Oauth2Credentials).order_by(
            desc(Oauth2Credentials.date)
        ):
            return credentials

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        calendars = settings["calendars"]
        max_items = settings.get("max_items", self.default_max_items)

        cred = self.get_credentials()
        # TODO Retrieve a new token, if none could be found
        #   if "oauth2_credentials" not in flask.session:
        #     return flask.redirect(flask.url_for("oauth2"))

        credentials = google.oauth2.credentials.Credentials(
            client_id=cred.client_id,
            client_secret=cred.client_secret,
            token=cred.token,
            token_uri=cred.token_uri
        )

        service = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, credentials=credentials
        )

        events, events_json = self.get_events(service, calendars, max_items)
        context = self.get_context(events=events, events_json=events_json)
        return render_template(self.template_name, **context)

    def get_events(self, api_service, calendars, max_items):
        all_events = []
        # Use the value from config
        calendar_list = api_service.calendarList().list().execute()
        calendar_items = calendar_list.get("items")
        [
            current_app.logger.info("%s: %s", i["id"], i["summary"])
            for i in calendar_items
        ]
        cals_filtered = [
            ci for ci in calendar_items if ci["summary"].lower() in calendars
        ]
        current_app.logger.info("%s", cals_filtered)
        if not cals_filtered:
            # TODO Render error page with message
            current_app.logger.error("Could not find calendar with names %s", calendars)
            return
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

    @staticmethod
    def _parse_event_data(event):
        start = event["start"].get("dateTime")
        type = "time"
        if start is None:
            start = event["start"].get("date")
            type = "day"
        end = event["end"].get("dateTime")
        if end is None:
            end = event["end"].get("date")
        return {
            "summary": event["summary"],
            # start.date -> whole day
            # start.dateTime -> specific time
            "start": dtparse(start),
            "end": dtparse(end),
            # The type reflects either whole day events or a specific time span
            "type": type,
            "location": event.get("location"),
        }


class MapView(FlirrorMethodView):

    endpoint = "map"
    rule = "/map"
    template_name = "map.html"

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        context = self.get_context(**settings)
        return render_template(self.template_name, **context)
