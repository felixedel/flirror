import logging
import time
from typing import Dict, Optional

from flask import current_app, Response
from pyowm import OWM
from pyowm.commons.exceptions import InvalidSSLCertificateError, UnauthorizedError
from pyowm.utils import config as pyowmconfig
from pyowm.weatherapi25.weather import Weather

from flirror.exceptions import CrawlerConfigError, CrawlerDataError
from flirror.modules import FlirrorModule


LOGGER = logging.getLogger(__name__)

WEATHER_ICONS = {
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

DEFAULT_TEMP_UNIT = "celsius"
DEFAULT_LANGUAGE = "en"

# TODO (felix): Define some default values in FlirrorModule?
weather_module = FlirrorModule("weather", __name__, template_folder="templates")


# A template filter to find the correct weather icon by name
@weather_module.app_template_filter()
def weather_icon(icon_name: str) -> Optional[str]:
    return WEATHER_ICONS.get(icon_name)


@weather_module.view()
def get() -> Response:
    return current_app.basic_get(template_name="weather/index.html")


@weather_module.crawler()
def crawl(
    module_id: str,
    app,
    api_key: str,
    city: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    language: Optional[str] = None,
    temp_unit: Optional[str] = None,
) -> None:
    WeatherCrawler(module_id, app, api_key, city, lat, lon, language, temp_unit).crawl()


class WeatherCrawler:
    def __init__(
        self,
        module_id: str,
        app,
        api_key: str,
        city: Optional[str] = None,
        lat: Optional[str] = None,
        lon: Optional[str] = None,
        language: Optional[str] = None,
        temp_unit: Optional[str] = None,
    ):
        self.module_id = module_id
        self.app = app
        self.api_key = api_key
        self.city = city
        self.lat = lat
        self.lon = lon
        self.language = language or DEFAULT_LANGUAGE
        self.temp_unit = temp_unit or DEFAULT_TEMP_UNIT
        self._owm = None

        # Simplify the condition when which lookup should be used.
        # Use coordinates for weather lookup if lat/lon are set, otherwise
        # use the city.
        self.use_coordinates = self.lat and self.lon
        self.use_city = not self.use_coordinates and self.city

    def crawl(self) -> None:
        # TODO (felix): It would be nice if the config could be validated
        # directly on start of flirror-crawler. Otherwise, the user will be
        # notified first when the crawler runs.
        if not any([self.use_coordinates, self.use_city]):
            raise CrawlerConfigError(
                "Either lat and lon or the city parameter must be provided"
            )

        # Look up lat/lon values for given city
        if self.use_city:
            LOGGER.info("Requesting weather data from OWM for city '%s'", self.city)
            # Using the one-call API only works with lat/long values. Thus, we
            # must look up those values first for the given city. However, the
            # city registry only contains larger cities and thus might not
            # return entry in any case.
            # TODO (felix): Define a method to retrieve the city and use
            # lru_cache to not always retrieve the info from the API again
            # (lat/lon for a given city shouldn't change too often ;-))
            LOGGER.debug(
                "Using city registry to retrieve lat/lon values for '%s'", self.city
            )

            # Please mypy: This codepath should be unreachable due to the
            # "if self.use_city" check, but mypy complains about the
            # city.split() call because city might be None.
            if not self.city:
                raise CrawlerDataError("Cannnot lookup city 'None' in city registry.")
            reg = self.owm.city_id_registry()
            city_name, _, country = self.city.partition(",")
            list_of_locations = reg.locations_for(
                city_name.strip(), country=country.strip()
            )
            if not list_of_locations:
                raise CrawlerDataError(
                    f"Could not find '{self.city}' in city registry. Please specify the "
                    "corresponding lat/lon values directly in the module's config."
                )

            city = list_of_locations[0]
            self.lat = city.lat
            self.lon = city.lon

        if self.use_coordinates:
            if self.city:
                LOGGER.info(
                    "Requesting weather data from OWM for city '%s' using coordinates "
                    "'%s,%s'",
                    self.city,
                    self.lat,
                    self.lon,
                )
            else:
                LOGGER.info(
                    "Requesting weather data from OWM for coordinates '%s,%s'",
                    self.lat,
                    self.lon,
                )

        now = time.time()

        # Use the one call API for the given lat/lon values to retrieve current
        # weather + forecast for the next 7 days
        one_call = self.owm.weather_manager().one_call(lat=self.lat, lon=self.lon)

        weather_data = self._parse_weather_data(one_call.current, self.temp_unit)
        # The one call API does not provide all temperature information we had
        # before in the current weather object. But we can add those from the
        # first forecast entry as it also covers the current day.
        today_temperature = one_call.forecast_daily[0].temperature(self.temp_unit)
        weather_data["temp_min"] = today_temperature.get("min")
        weather_data["temp_max"] = today_temperature.get("max")

        # Add the parameters with which the crawler was invoked
        weather_data["city"] = self.city
        weather_data["lat"] = self.lat
        weather_data["lon"] = self.lon
        weather_data["forecasts"] = []

        # Skip the first element as we already have the weather for today
        for fc_weather in list(one_call.forecast_daily)[1:7]:
            fc_data = self._parse_weather_data(fc_weather, self.temp_unit)
            weather_data["forecasts"].append(fc_data)

        # Store the crawl timestamp
        weather_data["_timestamp"] = now

        self.app.store_module_data(self.module_id, weather_data)

    @property
    def owm(self) -> OWM:
        if self._owm is None:
            LOGGER.debug("Authenticating to OWM API")
            # Sadly, pyowm provides a default configuration, but it's only used
            # in case we don't provide any. So, unless we want to specify all
            # default values by ourselves, we must merge the dictionaries
            # before
            config = pyowmconfig.get_default_config()
            config["language"] = self.language
            try:
                self._owm = OWM(self.api_key, config=config)
            except UnauthorizedError as e:
                LOGGER.error("Unable to authenticate to OWM API")
                raise CrawlerDataError from e
            # Despite the name, this exception seems to be raised if no
            # connection is possible at all (e.g. no network/internet
            # connection).
            except InvalidSSLCertificateError:
                raise CrawlerDataError("Could not connect to OWM API")
        return self._owm

    @staticmethod
    def _parse_weather_data(weather: Weather, temp_unit: str) -> Dict:
        temperature = weather.temperature(temp_unit)
        return {
            "date": weather.ref_time,
            # Current temperature is only available for the current weather
            "temp_cur": temperature.get("temp"),
            # Day/night temperatures are only available for forecast data, not
            # for the current weather.
            "temp_day": temperature.get("day"),
            "temp_night": temperature.get("night"),
            "status": weather.status,
            "detailed_status": weather.detailed_status,
            "sunrise_time": weather.srise_time,
            "sunset_time": weather.sset_time,
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon": weather.weather_icon_name,
        }
