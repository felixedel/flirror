import logging

from flask import jsonify, request

from flirror.exceptions import ModuleDataException
from flirror.modules import FlirrorModule
from flirror.views import get_module_data, json_abort


LOGGER = logging.getLogger(__name__)

FLIRROR_OBJECT_KEY = "module_weather"

weather_module = FlirrorModule("weather", __name__, template_folder="templates")


@weather_module.route("/")
def get():
    module_id = request.args.get("module_id")
    output = request.args.get("output")  # other: raw

    try:
        data = get_module_data(
            module_id, output, "weather/index.html", FLIRROR_OBJECT_KEY
        )
        return jsonify(data)
    except ModuleDataException as e:
        json_abort(400, str(e))
