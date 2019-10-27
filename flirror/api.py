from flask import abort, current_app, jsonify, make_response, render_template, request

from flirror.database import get_object_by_key
from flirror.views import FlirrorMethodView


def json_abort(status, msg=None):
    response = {"error": status}
    if msg is not None:
        response["msg"] = msg
    abort(make_response(jsonify(response), status))


class FlirrorApiView(FlirrorMethodView):
    def get(self):
        # Get view specifc settings from config
        self.module_id = request.args.get("module_id")
        self.module_config = [
            m for m in current_app.config.get("MODULES") if m["id"] == self.module_id
        ]
        output_type = request.args.get("output")  # other: raw

        if output_type not in ["template", "raw"]:
            json_abort(
                400, "Missing 'output' parameter. Must be one of: ['template', 'raw']."
            )

        # TODO if output == "template" -> provide only the _template parameter
        # -> That's how the API must be called via ajax
        # TODO if output == "raw" -> provide the JSON API "as is" without _template
        # -> That's how the API must be called from the the index view
        # (for initial loading)

        if self.module_config:
            self.module_config = self.module_config[0]
        else:
            # TODO Error handling or just crash?
            json_abort(
                400,
                f"Could not find any module config for ID '{self.module_id}'. "
                "Are your sure this one is specified in the config file?",
            )
            pass

        # The data must be retrieved in both cases, template and raw
        data = self.get_data()

        # TODO Check if data is None

        if output_type == "raw":
            return jsonify(data)
        else:
            context = {
                "module": {
                    "type": self.module_config["type"],
                    "id": self.module_id,
                    "config": self.module_config["config"],
                    "display": self.module_config["display"],
                    "error": None,  # TODO What about that?
                    "data": data,
                }
            }

            template = render_template(self.template_name, **context)
            return jsonify(_template=template)


class WeatherApi(FlirrorApiView):

    endpoint = "api-weather"
    rule = "/api/weather"
    template_name = "modules/weather.html"

    FLIRROR_OBJECT_KEY = "module_weather"

    def get_data(self):
        db = current_app.extensions["database"]
        weather = get_object_by_key(db, f"{self.FLIRROR_OBJECT_KEY}-{self.module_id}")

        if weather is None:
            # How to deal with that in ajax?
            # That would result in an error callback, so we might be able to
            # template the error directly and only insert the message.
            json_abort(
                400,
                f"Could not find weather data for module with ID '{self.module_id}'. "
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


class NewsfeedApi(FlirrorMethodView):

    endpoint = "api-newsfeed"
    rule = "/api/newsfeed"
    template_name = None

    FLIRROR_OBJECT_KEY = "module_newsfeed"

    def get(self):
        module_id = request.args.get("module_id")
        db = current_app.extensions["database"]
        data = get_object_by_key(db, f"{self.FLIRROR_OBJECT_KEY}-{module_id}")

        if data is None:
            json_abort(
                400,
                f"Could not find calendar data for module with ID '{module_id}'. "
                "Did the appropriate crawler run?",
            )

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
