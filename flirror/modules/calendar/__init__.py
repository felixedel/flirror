import logging
import time
from datetime import datetime

import arrow
import googleapiclient.discovery
from flask import current_app
from google.auth.exceptions import RefreshError

from flirror.modules import FlirrorModule
from flirror.crawler.google_auth import GoogleOAuth
from flirror.exceptions import CrawlerDataError

LOGGER = logging.getLogger(__name__)

FLIRROR_OBJECT_KEY = "module_calendar"

calendar_module = FlirrorModule(
    "calendar",
    __name__,
    # TODO (felix): Do we always need to specify the rest?
)


@calendar_module.route("/")
def get():
    return current_app.basic_get(
        template_name="calendar/index.html", flirror_object_key=FLIRROR_OBJECT_KEY
    )


@calendar_module.crawler("calendar-crawler")
def crawl(crawler_id, database, calendars, max_items):
    CalendarCrawler(crawler_id, database, calendars, max_items).crawl()


class CalendarCrawler:

    DEFAULT_MAX_ITEMS = 5
    # TODO Maybe we could use this also as a fallback if no calendar from the list matched
    DEFAULT_CALENDAR = "primary"

    API_SERVICE_NAME = "calendar"
    API_VERSION = "v3"

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(
        self,
        crawler_id,
        database,
        calendars,
        max_items=DEFAULT_MAX_ITEMS,
        interval=None,
    ):
        super().__init__(crawler_id, database, interval)
        self.calendars = calendars
        self.max_items = max_items

    def crawl(self):
        try:
            credentials = GoogleOAuth(
                self.database, self.SCOPES, self.object_key
            ).get_credentials()
        except ConnectionError:
            raise CrawlerDataError("Unable to connect to Google API")
        if not credentials:
            raise CrawlerDataError("Unable to authenticate to Google API")

        # Get the current time to store in the calender events list in the database
        now = time.time()

        LOGGER.info("Requesting calendar list from Google API")
        service = googleapiclient.discovery.build(
            self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials
        )

        try:
            calendar_list = service.calendarList().list().execute()
        except RefreshError:
            # Google responds with a RefreshError when the token is invalid as it
            # would try to refresh the token if the necessary fields are set
            # which we haven't)
            raise CrawlerDataError(
                "Could not retrieve calendar list. Maybe flirror doesn't have "
                "the permission to access your calendar."
            )

        calendar_items = calendar_list.get("items")

        cals_filtered = [
            ci for ci in calendar_items if ci["summary"].lower() in self.calendars
        ]
        if not cals_filtered:
            raise CrawlerDataError(
                "None of the provided calendars matched the list I got from Google: {}".format(
                    self.calendars
                )
            )

        all_events = []
        for cal_item in cals_filtered:
            # Call the calendar API
            _now = "{}Z".format(datetime.utcnow().isoformat())  # 'Z' indicates UTC time
            LOGGER.info(
                "Requesting upcoming %d events for calendar '%s'",
                self.max_items,
                cal_item["summary"],
            )
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
            if not events:
                LOGGER.warning(
                    "Could not find any upcoming events for calendar '%s",
                    cal_item["summary"],
                )
            for event in events:
                all_events.append(self._parse_event_data(event))

        # Sort the events from multiple calendars
        all_events = sorted(all_events, key=lambda k: k["start"])

        event_data = {"_timestamp": now, "events": all_events[: self.max_items]}
        # TODO (felix): Provide back reference to app in register_crawler() so
        # we don't need a request context here and can use app.store_...()
        # instead of current_app.store...()
        current_app.store_module_data(
            self.crawler_id, FLIRROR_OBJECT_KEY, data=event_data
        )

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
        start = arrow.get(start).replace(tzinfo=None).timestamp
        end = arrow.get(end).replace(tzinfo=None).timestamp

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