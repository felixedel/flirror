from flask import Flask


FLIRROR_SETTINGS_ENV = "FLIRROR_SETTINGS"


def create_app():
    app = Flask(__name__)
    app.config.from_envvar(FLIRROR_SETTINGS_ENV)

    return app


app = create_app()

# Load all views
# TODO (felix): Not very nice, but for an initial show case ok.
#  We should switch to problems for a "productive" system, otherwise
#  we would have to define all routes inside this __init__.py file.
import flirror.views
