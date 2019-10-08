from flask import abort, current_app, jsonify, make_response, request

from flirror.database import get_object_by_key
from flirror.views import FlirrorMethodView


def json_abort(status, msg=None):
    response = {"error": status}
    if msg is not None:
        response["msg"] = msg
    abort(make_response(jsonify(response), status))


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
        module_id = request.args.get("module_id")
        db = current_app.extensions["database"]
        weather = get_object_by_key(db, f"{self.FLIRROR_OBJECT_KEY}-{module_id}")

        if weather is None:
            json_abort(
                400,
                f"Could not find weather data for module with ID '{module_id}'. "
                "Did the appropriate crawler run?",
            )

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
        module_id = request.args.get("module_id")
        db = current_app.extensions["database"]
        data = get_object_by_key(db, f"{self.FLIRROR_OBJECT_KEY}-{module_id}")

        if data is None:
            json_abort(
                400,
                f"Could not find calendar data for module with ID '{module_id}'. "
                "Did the appropriate crawler run?",
            )

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
        module_id = request.args.get("module_id")
        db = current_app.extensions["database"]
        data = get_object_by_key(db, f"{self.FLIRROR_OBJECT_KEY}-{module_id}")

        if data is None:
            json_abort(
                400,
                f"Could not find stocks data for module with ID '{module_id}'. "
                "Did the appropriate crawler run?",
            )

        return data
