from flask import current_app, jsonify

from flirror.database import get_object_by_key
from flirror.views import FlirrorMethodView


class WeatherApi(FlirrorMethodView):

    endpoint = "api-weather"
    rule = "/api/weather"
    template_name = None

    FLIRROR_OBJECT_KEY = "module_weather"

    def get(self):
        # TODO Get view-specific settings from config
        # settings = current_app.config["MODULES"].get(self.endpoint)
        # city = settings.get("city")

        # Get weather data from database
        weather = self.get_weather()
        return jsonify(weather)

    def get_weather(self):
        db = current_app.extensions["database"]
        weather = get_object_by_key(db, self.FLIRROR_OBJECT_KEY)
        # Change timestamps to datetime objects
        # TODO This should be done before storing the data, but I'm not sure
        # how to tell Pony how to serialize the datetime to JSON
        return weather


class CalendarApi(FlirrorMethodView):

    endpoint = "api-calendar"
    rule = "/api/calendar"
    template_name = None

    FLIRROR_OBJECT_KEY = "module_calendar"

    def get(self):
        data = self.get_events()
        return jsonify(data)

    def get_events(self):
        db = current_app.extensions["database"]
        data = get_object_by_key(db, self.FLIRROR_OBJECT_KEY)
        # Change timestamps to datetime objects
        # TODO This should be done before storing the data, but I'm not sure
        # how to tell Pony how to serialize the datetime to JSON
        return data


class StocksApi(FlirrorMethodView):

    endpoint = "api-stocks"
    rule = "/api/stocks"
    template_name = None

    FLIRROR_OBJECT_KEY = "module_stocks"

    def get(self):
        data = self.get_stocks()
        return jsonify(data)

    def get_stocks(self):
        db = current_app.extensions["database"]
        data = get_object_by_key(db, self.FLIRROR_OBJECT_KEY)
        return data
