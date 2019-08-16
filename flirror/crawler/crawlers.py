import logging
import time
from datetime import datetime

import googleapiclient.discovery
from dateutil.parser import parse as dtparse
from google.auth.exceptions import RefreshError
from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError

from flirror.database import store_object_by_key
from flirror.exceptions import CrawlerDataError
from flirror.crawler.google_auth import GoogleOAuth

LOGGER = logging.getLogger(__name__)


class WeatherCrawler:

    FLIRROR_OBJECT_KEY = "module_weather"

    def __init__(self, api_key, language, city, temp_unit):
        self.api_key = api_key
        self.language = language
        self.city = city
        self.temp_unit = temp_unit
        self._owm = None

    def crawl(self):
        try:
            obs = self.owm.weather_at_place(self.city)
        except UnauthorizedError as e:
            raise CrawlerDataError from e

        # Get today's weather and weekly forecast
        weather = obs.get_weather()

        weather_data = self._parse_weather_data(weather, self.temp_unit, self.city)

        # Get the forecast for the next days
        fc = self.owm.daily_forecast(self.city, limit=7)

        # Skip the first element as we already have the weather for today
        for fc_weather in list(fc.get_forecast())[1:]:
            fc_data = self._parse_forecast_data(fc_weather, self.temp_unit)
            weather_data["forecasts"].append(fc_data)

        store_object_by_key(key=self.FLIRROR_OBJECT_KEY, value=weather_data)

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
            "date": weather.get_reference_time(),
            "temp_cur": temp_dict["temp"],
            "temp_min": temp_dict["temp_min"],
            "temp_max": temp_dict["temp_max"],
            "status": weather.get_status(),
            "detailed_status": weather.get_detailed_status(),
            "sunrise_time": weather.get_sunrise_time(),
            "sunset_time": weather.get_sunset_time(),
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon": weather.get_weather_icon_name(),
            "forecasts": [],
        }

    @staticmethod
    def _parse_forecast_data(forecast, temp_unit):
        temperature = forecast.get_temperature(unit=temp_unit)
        return {
            "date": forecast.get_reference_time(),
            "temp_day": temperature["day"],
            "temp_night": temperature["night"],
            "status": forecast.get_status(),
            "detailed_status": forecast.get_detailed_status(),
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon": forecast.get_weather_icon_name(),
        }


class CalendarCrawler:

    FLIRROR_OBJECT_KEY = "module_calendar"

    DEFAULT_MAX_ITEMS = 5
    # TODO Maybe we could use this also as a fallback if no calendar from the list matched
    DEFAULT_CALENDAR = "primary"

    API_SERVICE_NAME = "calendar"
    API_VERSION = "v3"

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, calendars, max_items=DEFAULT_MAX_ITEMS):
        self.calendars = calendars
        self.max_items = max_items

    def crawl(self):
        credentials = GoogleOAuth(self.SCOPES).get_credentials()

        # Get the current time to store in the calender events list in the database
        now = time.time()

        service = googleapiclient.discovery.build(
            self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials
        )

        try:
            # TODO Error on initial request (with initial access token):
            #  ValueError: {'access_token': 'ya29.GltTB4hSMZCww2snLPzpma0Fkq9vriYAjdySDTiSfYdiCKupTczbbv5hwevK4DAV2r7mfXi4wMiV2cmYFSpWyaP3ukHGTUkWPLI3Z2B0YrwxqO4f9ycbS39yj3SS',
            #  'expires_in': 1564303934.249835, 'refresh_token': '1/OrhaTqqkK349FgaGOwzjSN-j0JxsZfKbNRKyDPS3kzI',
            #  'scope': 'https://www.googleapis.com/auth/calendar.readonly', 'token_type': 'Bearer'}
            #  could not be converted to unicode
            calendar_list = service.calendarList().list().execute()
        except RefreshError:
            # Google responds with a RefreshError when the token is invalid as it
            # would try to refresh the token if the necessary fields are set
            # which we haven't)
            LOGGER.error(
                "Look's like flirror doesn't have the permission to access "
                "your calendar."
            )
            return

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
            _now = "{}Z".format(datetime.utcnow().isoformat())  # 'Z' indicates UTC time
            LOGGER.info("Getting the upcoming 10 events")
            events_result = (
                service.events()
                .list(
                    calendarId=cal_item["id"],
                    timeMin=_now,
                    maxResults=self.max_items,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            event_data = {"date": now, "events": []}
            for event in events:
                event_data["events"].append(self._parse_event_data(event))

            store_object_by_key(key=self.FLIRROR_OBJECT_KEY, value=event_data)

        # Sort the events from multiple calendars, but ignore the timezone
        # TODO Is that still needed when we have a database?
        # all_events = sorted(all_events, key=lambda k: k["start"].replace(tzinfo=None))
        # return all_events[: self.max_items]

    @staticmethod
    def _parse_event_data(event):
        start = event["start"].get("dateTime")
        event_type = "time"
        if start is None:
            start = event["start"].get("date")
            event_type = "day"
        end = event["end"].get("dateTime")
        if end is None:
            end = event["end"].get("date")

        # Convert strings to dates and set timezone info to none,
        # as not all entries have time zone infos
        # TODO: How to fix this?
        start = dtparse(start).replace(tzinfo=None).timestamp()
        end = dtparse(end).replace(tzinfo=None).timestamp()

        return dict(
            summary=event["summary"],
            # start.date -> whole day
            # start.dateTime -> specific time
            start=start,
            end=end,
            # The type reflects either whole day events or a specific time span
            type=event_type,
            location=event.get("location"),
        )
