import abc
from datetime import datetime

import flask
import google.oauth2.credentials
import googleapiclient.discovery
from dateutil.parser import parse as dtparse
from flask import abort, current_app, render_template
from flask.views import MethodView
from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError


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
        "02n": "wi wi-night-alt-cloudy",
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

        try:
            # Create OWM client
            owm = OWM(API_key=api_key, language=language, version="2.5")
            obs = owm.weather_at_place(city)
        except UnauthorizedError as e:
            abort(403, "We are unable to retrieve weather information: {}".format(e))

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

    api_scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
    api_service_name = "calendar"
    api_version = "v3"

    # TODO Maybe we could use this also as a fallback if no calendar from the list matched
    default_calendars = ["primary"]
    default_max_items = 5

    def get(self):
        # Get view-specific settings from config
        settings = current_app.config["MODULES"].get(self.endpoint)
        calendars = settings["calendars"]
        max_items = settings.get("max_items", self.default_max_items)
        if "oauth2_credentials" not in flask.session:
            return flask.redirect(flask.url_for("oauth2"))

        # Load credentials from the session
        credentials = google.oauth2.credentials.Credentials(
            **flask.session["oauth2_credentials"]
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
