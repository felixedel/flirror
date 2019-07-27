import logging
import os
from datetime import datetime
from time import time

import google.oauth2.credentials
import googleapiclient.discovery
import requests
from dateutil.parser import parse as dtparse
from google_auth_oauthlib.flow import Flow
from pony.orm import db_session, desc, select
from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError

from flirror.database import (
    CalendarEvent,
    Misc,
    Oauth2Credentials,
    Weather,
    WeatherForecast,
)
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

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    GOOGLE_OAUTH_ACCESS_URL = "https://accounts.google.com/o/oauth2/device/code"
    GOOGLE_OAUTH_POLL_URL = "https://www.googleapis.com/oauth2/v4/token"

    def __init__(self, calendars, max_items=DEFAULT_MAX_ITEMS):
        self.calendars = calendars
        self.max_items = max_items

    def crawl(self):
        token = self.authenticate()
        if token is None:
            LOGGER.warning("Authentication failed. Cannot retrieve calendar data")
            raise CrawlerDataError(
                "Authentication failed. Cannot retrieve calendar data"
            )

        flow = self._get_oauth_flow()

        # TODO Get client_id and secret from flow
        credentials = google.oauth2.credentials.Credentials(
            client_id=flow.client_config["client_id"],
            client_secret=flow.client_config["client_secret"],
            token=token,
            #token_uri=cred.token_uri,
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

    @db_session
    def authenticate(self):
        # Check if we already have a valid token
        query = Misc.select(lambda m: m.key == "google_oauth_token")
        token_obj = query.first()
        # TODO If token_obj is None or token_obj.expired_in <= now
        if token_obj is None:
            LOGGER.debug("Could not find any token. Requesting a new one.")
            # TODO Initial request with device_code necessary
            token = self.initial_access_token()
        else:
            now = time()
            if token_obj.value["expires_in"] <= now:
                LOGGER.debug("Found a token, but expired. Requesting a new one.")
                # TODO Use the refresh_token to get a new one
                token = self.refresh_access_token(token_obj.value["refresh_token"])
            else:
                token = token_obj.value["access_token"]

        # Hopefully, we got a token in any case now
        return token

    @db_session
    def refresh_access_token(self, refresh_token):
        # Use the refresh token to request a new access token
        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "grant_type": refresh_token,
        }

        now = time()
        res = requests.post(self.GOOGLE_OAUTH_POLL_URL, data=data)
        LOGGER.info(res.status_code)
        LOGGER.info(res.content)

        # TODO Error handling (e.g. offline)?
        value = res.json()
        # Calculate an absolute expiry timestamp for simpler evaluation
        value["expires_in"] += now
        # Store the device in the database for later usage
        Misc(key="google_oauth_token", value=value)
        return value

    @db_session
    def initial_access_token(self):
        # We need at least a (valid) device code for the initial token request
        device = self.ask_for_access()
        if device is None:
            LOGGER.error("Unable to retrieve data. You have to provide access first")
            return

        # If we have a valid (not expired) device code, we can use this for an initial request
        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "code": device["device_code"],
            "grant_type": "http://oauth.net/grant_type/device/1.0",
        }

        now = time()
        res = requests.post(self.GOOGLE_OAUTH_POLL_URL, data=data)

        # TODO Error handling (e.g. offline)?
        value = res.json()
        # Calculate an absolute expiry timestamp for simpler evaluation
        value["expires_in"] += now
        # Store the device in the database for later usage
        Misc(key="google_oauth_token", value=value)
        return value

    @db_session
    def ask_for_access(self):
        LOGGER.debug("Checking if device code is already available")
        device = None
        query = Misc.select(lambda m: m.key == "google_oauth_device")
        device_obj = query.first()

        # If nothing could be found, we need to request a new one
        if device_obj is None:
            LOGGER.debug("No device code found, requesting a new one")
        else:
            # Check if device code is still valid
            now = time()
            if device_obj.value["expires_in"] <= now:
                LOGGER.debug("Device code found, but expired. Requesting a new one")
            else:
                device = device_obj.value

        if device is not None:
            return device

        # If we got no device so far, we need the user to grant us permission first
        self._ask_for_access()
        # Use this as indicator to stop the authentication flow as it doesn't
        # make sense to continue until the access is granted by the user.
        return None

    def _ask_for_access(self):
        # Store current timestamp to calculate an absolute expiry date
        now = time()

        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "scope": " ".join(self.SCOPES),
        }

        res = requests.post(self.GOOGLE_OAUTH_ACCESS_URL, data=data)
        LOGGER.info(res.status_code)
        LOGGER.info(res.content)

        # TODO Error handling (e.g. offline)?
        device = res.json()
        # Calculate an absolute expiry timestamp for simpler evaluation
        device["expires_in"] += now
        # Store the device in the database for later usage
        Misc(key="google_oauth_device", value=device)

        LOGGER.info(
            "Please visit '%s' and enter '%s'",
            device["verification_url"],
            device["user_code"],
        )
        # TODO Show a QR code pointing to the URL + entering the code

        return device

    def _get_oauth_flow(self):
        client_secret_file = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        if client_secret_file is None:
            LOGGER.warning(
                "Environment variable 'GOOGLE_OAUTH_CLIENT_SECRET' "
                "must be set and point to a valid client-secret.json file"
            )
            return

        # Let the flow creation parse the client_secret file
        flow = Flow.from_client_secrets_file(client_secret_file, scopes=self.SCOPES)
        return flow
