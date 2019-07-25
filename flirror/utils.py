
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
