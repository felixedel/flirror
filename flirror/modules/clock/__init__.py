import logging

from flask import current_app, jsonify, render_template, request, Response

from flirror.modules import FlirrorModule

LOGGER = logging.getLogger(__name__)

clock_module = FlirrorModule("clock", __name__, template_folder="templates")


@clock_module.view()
def get() -> Response:
    # The clock module only uses a subset of the flirror.basic_get() method as
    # it does not need to access the database.
    module_id = request.args.get("module_id")
    if not module_id:
        return current_app.json_abort(400, "Parameter 'module_id' is missing")
    module_configs = [
        m for m in current_app.config.get("MODULES", {}) if m.get("id") == module_id
    ]
    if module_configs:
        module_config = module_configs[0]
    else:
        return current_app.json_abort(
            400,
            f"Could not find any module config for ID '{module_id}'. "
            "Are you sure this one is specified in the config file?",
        )

    context = {
        "module": {
            "module": "clock",
            "id": module_id,
            "config": module_config["config"],
        }
    }
    data = {"_template": render_template("clock/index.html", **context)}
    return jsonify(data)
