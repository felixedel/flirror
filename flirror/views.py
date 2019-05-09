from flask import current_app, render_template

from flirror import app


@app.route("/")
def index():
    return render_template("index.html", **current_app.config["MODULES"])


@app.route("/weather")
def weather():
    # TODO We could keep the name, etc. when changing to a class based approach
    name = "weather"
    # Get view-specific settings from config
    settings = current_app.config["MODULES"].get(name)
    return render_template("weather.html", **settings)


@app.route("/calendar")
def calendar():
    name = "calendar"
    # Get view-specific settings from config
    settings = current_app.config["MODULES"].get(name)
    return render_template("calendar.html", **settings)


@app.route("/map")
def map():
    name = "map"
    # Get view-specific settings from config
    settings = current_app.config["MODULES"].get(name)
    return render_template("map.html", **settings)
