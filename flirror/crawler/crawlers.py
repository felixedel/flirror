import logging
from datetime import datetime

import google.oauth2.credentials
import googleapiclient.discovery
from dateutil.parser import parse as dtparse
from pony.orm import db_session, desc, select
from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError

from flirror.database import CalendarEvent, Oauth2Credentials, Weather, WeatherForecast
from flirror.exceptions import CrawlerDataError

LOGGER = logging.getLogger(__name__)


class WeatherCrawler:
    def __init__(self, api_key, language, city, temp_unit):
        self.api_key = api_key
        self.language = language
        self.city = city
        self.temp_unit = temp_unit
        self._owm = None

    @db_session
    def crawl(self):
        try:
            obs = self.owm.weather_at_place(self.city)
        except UnauthorizedError as e:
            raise CrawlerDataError from e

        # Get today's weather and weekly forecast
        weather = obs.get_weather()

        weather_data = self._parse_weather_data(weather, self.temp_unit, self.city)
        # Store the weather information in sqlite
        weather_obj = Weather(**weather_data)

        # Get the forecast for the next days
        fc = self.owm.daily_forecast(self.city, limit=7)

        # Skip the first element as we already have the weather for today
        for fc_weather in list(fc.get_forecast())[1:]:
            fc_data = self._parse_forecast_data(fc_weather, self.temp_unit)
            print(fc_data)
            # Store the forecast information in sqlite
            WeatherForecast(weather=weather_obj, **fc_data)

    @property
    def owm(self):
        if self._owm is None:
            self._owm = OWM(API_key=self.api_key, language=self.language, version="2.5")
        return self._owm

    @staticmethod
    def _parse_weather_data(weather, temp_unit, city):
        temp_dict = weather.get_temperature(unit=temp_unit)
        return {
            "city": city,
            "date": datetime.utcfromtimestamp(weather.get_reference_time()),
            "temp_cur": temp_dict["temp"],
            "temp_min": temp_dict["temp_min"],
            "temp_max": temp_dict["temp_max"],
            "status": weather.get_status(),
            "detailed_status": weather.get_detailed_status(),
            "sunrise_time": datetime.utcfromtimestamp(weather.get_sunrise_time()),
            "sunset_time": datetime.utcfromtimestamp(weather.get_sunset_time()),
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon": weather.get_weather_icon_name(),
        }

    @staticmethod
    def _parse_forecast_data(forecast, temp_unit):
        temperature = forecast.get_temperature(unit=temp_unit)
        return {
            "date": datetime.utcfromtimestamp(forecast.get_reference_time()),
            "temp_day": temperature["day"],
            "temp_night": temperature["night"],
            "status": forecast.get_status(),
            "detailed_status": forecast.get_detailed_status(),
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon": forecast.get_weather_icon_name(),
        }


class CalendarCrawler:

    DEFAULT_MAX_ITEMS = 5
    # TODO Maybe we could use this also as a fallback if no calendar from the list matched
    DEFAULT_CALENDAR = "primary"

    API_SERVICE_NAME = "calendar"
    API_VERSION = "v3"

    def __init__(self, calendars, max_items=DEFAULT_MAX_ITEMS):
        self.calendars = calendars
        self.max_items = max_items
        # TODO Make the smarmirror host and port configurable and get it from the config
        #   We need it to refresh the google oauth token if expired
        self.flirror_host = "localhost:5000"

    def crawl(self):
        cred = self.get_credentials()
        # TODO Retrieve a new token, if none could be found or the one found is
        # expired (got 403 from the google API)
        #   if "oauth2_credentials" not in flask.session:
        #     return flask.redirect(flask.url_for("oauth2"))
        # NOTE: Call the {flirror_host}/oauth2 endpoint with requests

        credentials = google.oauth2.credentials.Credentials(
            client_id=cred.client_id,
            client_secret=cred.client_secret,
            token=cred.token,
            token_uri=cred.token_uri,
        )

        service = googleapiclient.discovery.build(
            self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials
        )

        calendar_list = service.calendarList().list().execute()
        calendar_items = calendar_list.get("items")

        [LOGGER.info("%s: %s", i["id"], i["summary"]) for i in calendar_items]

        cals_filtered = [
            ci for ci in calendar_items if ci["summary"].lower() in self.calendars
        ]
        if not cals_filtered:
            raise CrawlerDataError(
                "Could not find calendar with names {}".format(self.calendars)
            )

        for cal_item in cals_filtered:
            # Call the calendar API
            now = "{}Z".format(datetime.utcnow().isoformat())  # 'Z' indicates UTC time
            LOGGER.info("Getting the upcoming 10 events")
            events_result = (
                service.events()
                .list(
                    calendarId=cal_item["id"],
                    timeMin=now,
                    maxResults=self.max_items,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            for event in events:
                self._parse_event_data(event)

        # Sort the events from multiple calendars, but ignore the timezone
        # TODO Is that still needed when we have a database?
        # all_events = sorted(all_events, key=lambda k: k["start"].replace(tzinfo=None))
        # return all_events[: self.max_items]

    @staticmethod
    @db_session
    def _parse_event_data(event):
        start = event["start"].get("dateTime")
        type = "time"
        if start is None:
            start = event["start"].get("date")
            type = "day"
        end = event["end"].get("dateTime")
        if end is None:
            end = event["end"].get("date")

        # Convert strings to dates and set timezone info to none,
        # as not all entries have time zone infos
        # TODO: How to fix this?
        start = dtparse(start).replace(tzinfo=None)
        end = dtparse(end).replace(tzinfo=None)

        CalendarEvent(
            summary=event["summary"],
            # start.date -> whole day
            # start.dateTime -> specific time
            start=start,
            end=end,
            # The type reflects either whole day events or a specific time span
            type=type,
            location=event.get("location"),
        )

    @staticmethod
    @db_session
    def get_credentials():
        # TODO There should only be one valid credentials entry in the database.
        #   How can we achieve this in a straight-forward way?
        for credentials in select(c for c in Oauth2Credentials).order_by(
            desc(Oauth2Credentials.date)
        ):
            return credentials
