import logging
import re
from datetime import datetime

import arrow


LOGGER = logging.getLogger(__name__)

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


def weather_icon(icon_name):
    return weather_icons.get(icon_name)


def prettydate(date):
    """
    Return the relative timeframe between the given date and now.
    e.g. 'Just now', 'x days ago', 'x hours ago', ...
    When the difference is greater than 7 days, the timestamp will be returned
    instead.
    """
    now = datetime.now()  # timezone.utc)
    if isinstance(date, float):
        date = datetime.utcfromtimestamp(date)
    diff = now - date
    # Show the timestamp rather than the relative timeframe when the difference
    # is greater than 7 days
    if diff.days > 7:
        return date.strftime("%d. %b %Y")
    return arrow.get(date).humanize()


def parse_interval_string(interval_string):
    # Split the string into <number><unit>
    pattern = re.compile(r"^(\d+)(\D+)$")
    match = pattern.match(interval_string)

    if not match:
        LOGGER.error("Could not parse interval_string '%s'", interval_string)
        return None, None

    interval = int(match.group(1))
    unit = match.group(2)

    return interval, unit


def format_time(timestamp, format):
    date = datetime.utcfromtimestamp(timestamp)
    return date.strftime(format)


def list_filter(list_of_dicts_to_filter, key):
    return [d[key] for d in list_of_dicts_to_filter]


def clean_string(string):
    """
    Taken from Django:
    https://github.com/django/django/blob/e3d0b4d5501c6d0bc39f035e4345e5bdfde12e41/django/utils/text.py#L222

    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    """
    string = str(string).strip().replace(" ", "_").replace("-", "_")
    return re.sub(r"(?u)[^-\w.]", "", string)
