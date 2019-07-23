import logging
from datetime import datetime

from pony.orm import db_session
from pyowm import OWM
from pyowm.exceptions.api_response_error import UnauthorizedError

from flirror.database import Weather, WeatherForecast
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
            "date": forecast.get_reference_time(timeformat="date"),
            "temp_day": temperature["day"],
            "temp_night": temperature["night"],
            "status": forecast.get_status(),
            "detailed_status": forecast.get_detailed_status(),
            # TODO For the forecast we don't need the "detailed" icon
            #  (no need to differentiate between day/night)
            "icon": forecast.get_weather_icon_name(),
        }
