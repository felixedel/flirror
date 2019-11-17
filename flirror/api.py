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

        # TODO template/raw output?
        if output_type not in ["template", "raw"]:
            json_abort(
                400, "Missing 'output' parameter. Must be one of: ['template', 'raw']."
            )

        if self.module_config:
            self.module_config = self.module_config[0]
        else:
            # TODO template/raw output?
            json_abort(
                400,
                f"Could not find any module config for ID '{self.module_id}'. "
                "Are your sure this one is specified in the config file?",
            )

        # Retrieve the data
        data = self.get_data()

        # Return the data either in raw format or as template
        if output_type == "raw":
            if data is None:
                json_abort(
                    400,
                    f"Could not find any data for module with ID '{self.module_id}'. "
                    "Did the appropriate crawler run?",
                )

            return jsonify(data)

        error = None
        if data is None:
            error = {
                # TODO Which error code should we use here?
                "code": 400,
                "msg": (
                    f"Could not find any data for module with ID '{self.module_id}'. "
                    "Did the appropriate crawler run?"
                ),
            }

        # Build template context and return template via JSON
        context = {
            "module": {
                "type": self.module_config["type"],
                "id": self.module_id,
                "config": self.module_config["config"],
                "display": self.module_config["display"],
                "error": error,
                "data": data,
            }
        }

        template = render_template(self.template_name, **context)
        return jsonify(_template=template)

    def get_data(self):
        db = current_app.extensions["database"]
        data = get_object_by_key(db, f"{self.FLIRROR_OBJECT_KEY}-{self.module_id}")

        # Change timestamps to datetime objects
        # TODO This should be done before storing the data, but I'm not sure
        # how to tell Pony how to serialize the datetime to JSON

        return data


class WeatherApi(FlirrorApiView):

    endpoint = "api-weather"
    rule = "/api/weather"
    template_name = "modules/weather.html"

    FLIRROR_OBJECT_KEY = "module_weather"


class CalendarApi(FlirrorApiView):

    endpoint = "api-calendar"
    rule = "/api/calendar"
    template_name = "modules/calendar.html"

    FLIRROR_OBJECT_KEY = "module_calendar"


class NewsfeedApi(FlirrorApiView):

    endpoint = "api-newsfeed"
    rule = "/api/newsfeed"
    template_name = "modules/newsfeed.html"

    FLIRROR_OBJECT_KEY = "module_newsfeed"


class StocksApi(FlirrorApiView):

    endpoint = "api-stocks"
    rule = "/api/stocks"
    template_name = "modules/stocks.html"

    FLIRROR_OBJECT_KEY = "module_stocks"
