import logging

from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError

from flirror.exceptions import CrawlerDataError

LOGGER = logging.getLogger(__name__)


class WeatherCrawler:

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
        fc = self.owm.daily_forecast(self.city, limit=7)

        fc_data = []
        # Skip the first element as we already have the weather for today
        for fc_weather in list(fc.get_forecast())[1:]:
            fc_data.append(self._parse_weather_data(fc_weather, self.temp_unit))
        weather_data = self._parse_weather_data(weather, self.temp_unit)

        result = {"city": self.city, "weather": weather_data, "forecast": fc_data}
        print(result)

    @property
    def owm(self):
        if self._owm is None:
            self._owm = OWM(API_key=self.api_key, language=self.language, version="2.5")
        return self._owm

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
