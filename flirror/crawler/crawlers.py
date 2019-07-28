import logging
import os
from datetime import datetime
import time

import google.oauth2.credentials
import googleapiclient.discovery
import requests
from dateutil.parser import parse as dtparse
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import Flow
from pony.orm import db_session, CacheIndexError
from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError


from flirror.database import CalendarEvent, Misc, Weather, WeatherForecast
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
            return

        flow = self._get_oauth_flow()
        # TODO To let google refresh the token, we must specify the
        #  refresh_token and the token_uri (which we don't have in this OAuth flow).
        credentials = google.oauth2.credentials.Credentials(
            client_id=flow.client_config["client_id"],
            client_secret=flow.client_config["client_secret"],
            token=token,
        )

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
        LOGGER.debug("Check if we already have an access token")
        query = Misc.select(lambda m: m.key == "google_oauth_token")
        token_obj = query.first()
        # TODO If token_obj is None or token_obj.expired_in <= now
        if token_obj is None:
            LOGGER.debug("Could not find any access token. Requesting an initial one.")
            token = self.ask_for_access()
        else:
            now = time.time()
            if token_obj.value["expires_in"] <= now:
                LOGGER.debug(
                    "Found an access token, but expired. Requesting a new one."
                )
                # We use the refresh_token to get a new access token
                token = self.refresh_access_token(token_obj.value["refresh_token"])
            else:
                token = token_obj.value["access_token"]

        # Hopefully, we got a token in any case now
        return token

    @db_session
    def refresh_access_token(self, refresh_token):
        LOGGER.debug("Requesting a new access token using the last refresh token")
        # Use the refresh token to request a new access token
        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        now = time.time()
        res = requests.post(self.GOOGLE_OAUTH_POLL_URL, data=data)
        LOGGER.info(res.status_code)
        LOGGER.info(res.content)

        # TODO Error handling (e.g. offline)?
        token_data = res.json()
        # Calculate an absolute expiry timestamp for simpler evaluation
        token_data["expires_in"] += now
        self._store_access_token(token_data)
        return token_data

    def ask_for_access(self):
        # As the device code is only necessary for the initial token request,
        # we should do both in one go. Otherwise, there are too many edge cases
        # to cover and if something goes wrong or the user does not grant us
        # permission before the device code is expired, we have to start from
        # the beginning.

        # Store current timestamp to calculate an absolute expiry date
        now = time.time()

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

        LOGGER.info(
            "Please visit '%s' and enter '%s'",
            device["verification_url"],
            device["user_code"],
        )
        # TODO Show a QR code pointing to the URL + entering the code

        # TODO Poll google's auth server in the specified interval until
        #  a) the user has granted us permission and we get a valid access token
        #  b) The device code got expired (or another time out from our side)

        token_data = self.poll_for_initial_access_token(device)
        return token_data["access_token"]

    def poll_for_initial_access_token(self, device):
        # TODO Timeout, max_retries?
        # Theoretically, we can poll until the device code is expired (which is
        # 30 minutes)
        while time.time() < device["expires_in"]:
            try:
                now = time.time()
                token_data = self._initial_access_token(device)
                # Calculate an absolute expiry timestamp for simpler evaluation
                token_data["expires_in"] += now
                self._store_access_token(token_data)
                return token_data
            except requests.exceptions.HTTPError as e:
                LOGGER.error(
                    "Could not get initial access token. You might want "
                    "to grant us permission first: %s",
                    e,
                )
                # Should be around 5 secs
                time.sleep(device["interval"])

        """
        # Use requests's session adapter to deal with retries and timeout
        session = requests.Session()
        retry = Retry(
            total=10,
            read=10,
            connect=10,
            backoff_factor=1,
            status_forcelist=[428],
            method_whitelist={"GET", "POST"},
        )

        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        res = session.post(self.GOOGLE_OAUTH_POLL_URL, data=data)
        """

    def _initial_access_token(self, device):
        # Use the device code for an initial token request
        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "code": device["device_code"],
            "grant_type": "http://oauth.net/grant_type/device/1.0",
        }
        res = requests.post(self.GOOGLE_OAUTH_POLL_URL, data=data)
        # We catch this in the caller method
        res.raise_for_status()

        return res.json()

    @db_session
    def _store_access_token(self, token_data):
        try:
            # The most common case is to refresh an existing token, so there should
            # already be an existing database entry that we can update
            Misc["google_oauth_token"].value = token_data
        except CacheIndexError as e:
            if "instance with primary key google_oauth_token already exists" in str(e):
                # If we request a token for the first time, we don't have an entry in
                # the database yet and thus have to create one
                Misc(key="google_oauth_token", value=token_data)
            else:
                raise e

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
