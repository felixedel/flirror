import os

import pytest
from jinja2 import Undefined
from jinja2.exceptions import UndefinedError
from pony.orm import db_session

from flirror import create_web
from flirror.database import create_database_and_entities

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testdata")


@pytest.fixture(scope="function")
def mock_google_env(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_OAUTH_CLIENT_SECRET", os.path.join(FIXTURE_DIR, "client_secret.json")
    )


@pytest.fixture(scope="function")
def mock_empty_database(tmpdir):
    database_file = os.path.join(tmpdir, "test_database.sqlite")
    db = create_database_and_entities(
        provider="sqlite", filename=database_file, create_db=True
    )
    yield db
    db.disconnect()


@db_session()
def populate_database(db):
    # NOTE (felix): This is more or less a subset of the data contained in the
    # tests/testdata/database-dump.sql file but some of the datasets are shortened
    # to allow simpler assertiongs in these unit tests.
    # As the database-dump.sql file is mainly used for the CSS regression tests,
    # re-defining those datasets in here allows us to keep the unit and CSS tests
    # independently of each other and change on without affecting the other.
    db.FlirrorObject(
        key="module_weather-weather-frankfurt",
        value={
            "_timestamp": 1574874141.210646,
            "city": "Frankfurt, DE",
            "date": 1574873921,
            "detailed_status": "broken clouds",
            "icon": "04n",
            "status": "Clouds",
            "sunrise_time": 1574837244,
            "sunset_time": 1574868224,
            "temp_cur": 8.22,
            "temp_max": 10.0,
            "temp_min": 6.11,
            "forecasts": [
                {
                    "date": 1574938800,
                    "detailed_status": "light rain",
                    "icon": "10d",
                    "status": "Rain",
                    "temp_day": 9.86,
                    "temp_night": 7.62,
                },
                {
                    "date": 1575025200,
                    "detailed_status": "moderate rain",
                    "icon": "10d",
                    "status": "Rain",
                    "temp_day": 5.11,
                    "temp_night": 0.66,
                },
                {
                    "date": 1575111600,
                    "detailed_status": "light snow",
                    "icon": "13d",
                    "status": "Snow",
                    "temp_day": 2.27,
                    "temp_night": -2.7,
                },
                {
                    "date": 1575198000,
                    "detailed_status": "overcast clouds",
                    "icon": "04d",
                    "status": "Clouds",
                    "temp_day": 0.12,
                    "temp_night": -3.32,
                },
                {
                    "date": 1575284400,
                    "detailed_status": "few clouds",
                    "icon": "02d",
                    "status": "Clouds",
                    "temp_day": 1.4,
                    "temp_night": -4.05,
                },
                {
                    "date": 1575370800,
                    "detailed_status": "sky is clear",
                    "icon": "01d",
                    "status": "Clear",
                    "temp_day": 0.79,
                    "temp_night": -3.12,
                },
            ],
        },
    )

    db.FlirrorObject(
        key="module_weather-weather-hamburg",
        value={"_timestamp": 1574874141.210646, "other_keys": "are missing"},
    )

    db.FlirrorObject(
        key="module_calendar-calendar-my",
        value={
            "_timestamp": 1574874185.653769,
            "events": [
                {
                    "end": 1574931600,
                    "location": None,
                    "start": 1574928000,
                    "summary": "Important application",
                    "type": "time",
                },
                {
                    "end": 1575158400,
                    "location": None,
                    "start": 1575072000,
                    "summary": "Meet a friend",
                    "type": "day",
                },
                {
                    "end": 1575368100,
                    "location": None,
                    "start": 1575364500,
                    "summary": "Medical appointment",
                    "type": "time",
                },
                {
                    "end": 1575849600,
                    "location": None,
                    "start": 1575676800,
                    "summary": "Christmas Market",
                    "type": "day",
                },
                {
                    "end": 1575849600,
                    "location": None,
                    "start": 1575676800,
                    "summary": "Competition",
                    "type": "day",
                },
            ],
        },
    )

    db.FlirrorObject(
        key="module_newsfeed-news-tagesschau",
        value={
            "_timestamp": 1574874193.9532669,
            "news": [
                {
                    "link": "http://www.tagesschau.de/ausland/steudtner-freispruch-101.html",
                    "published": 1574861126.000002,
                    "summary": "Im Prozess gegen Menschenrechtsaktivisten in der Türkei hat die Staatsanwaltschaft Freispruch für den Berliner Steudtner und andere beantragt. Nach Angaben von Amnesty droht mehreren Mitangeklagten jedoch weiterhin Haft. Von Karin Senz.",
                    "title": "Istanbuler Staatsanwalt fordert überraschend Freispruch für Steudtner",
                },
                {
                    "link": "http://www.tagesschau.de/ausland/eu-kommission-vonderleyen-107.html",
                    "published": 1574861347.000002,
                    "summary": "Das EU-Parlament hat die neue Besetzung der EU-Kommission bestätigt. Damit können Ursula von der Leyen und ihr Team am Sonntag ihre Arbeit aufnehmen - mit einem Monat Verspätung.",
                    "title": "Von der Leyens EU-Kommission kann starten",
                },
                {
                    "link": "http://www.tagesschau.de/multimedia/bilder/eu-kommission-207.html",
                    "published": 1574820441.000002,
                    "summary": "Am 1. Dezember wird EU-Kommissionspräsidentin Ursula von der Leyen die Arbeit in Brüssel aufnehmen - mit einer neuen Kommission. Stephan Ueberbach gibt einen Überblick über die Mitglieder.",
                    "title": "Bilder: Das sind die neuen Mitglieder der EU-Kommission",
                },
            ],
        },
    )

    db.FlirrorObject(
        key="module_stocks-stocks-series",
        value={
            "_timestamp": 1574874186.4492302,
            "stocks": [
                {
                    "alias": "APPLE",
                    "data": {
                        "times": [
                            "2019-11-21 13:15:00",
                            "2019-11-21 13:30:00",
                            "2019-11-21 13:45:00",
                            "2019-11-21 14:00:00",
                            "2019-11-21 14:15:00",
                        ],
                        "values": [
                            {
                                "close": "262.1350",
                                "high": "262.4800",
                                "low": "262.1350",
                                "open": "262.1900",
                                "volume": "330109",
                            },
                            {
                                "close": "262.2900",
                                "high": "262.3320",
                                "low": "262.1100",
                                "open": "262.1400",
                                "volume": "239432",
                            },
                            {
                                "close": "262.0600",
                                "high": "262.3300",
                                "low": "261.9500",
                                "open": "262.3000",
                                "volume": "375336",
                            },
                            {
                                "close": "261.9200",
                                "high": "262.1500",
                                "low": "261.8800",
                                "open": "262.0700",
                                "volume": "334920",
                            },
                            {
                                "close": "262.0105",
                                "high": "262.3411",
                                "low": "261.7505",
                                "open": "261.9455",
                                "volume": "3446294",
                            },
                        ],
                    },
                }
            ],
        },
    )

    db.FlirrorObject(
        key="module_stocks-stocks-table",
        value={
            "_timestamp": 1574874188.9645052,
            "stocks": [
                {
                    "alias": "APPLE",
                    "data": {
                        "01. symbol": "AAPL",
                        "02. open": "265.5800",
                        "03. high": "266.6000",
                        "04. low": "265.3100",
                        "05. price": "266.4500",
                        "06. volume": "6318685",
                        "07. latest trading day": "2019-11-27",
                        "08. previous close": "264.2900",
                        "09. change": "2.1600",
                        "10. change percent": "0.8173%",
                    },
                    "symbol": "aapl",
                },
                {
                    "alias": "",
                    "data": {
                        "01. symbol": "GOOGL",
                        "02. open": "1315.4200",
                        "03. high": "1317.6400",
                        "04. low": "1309.4742",
                        "05. price": "1311.0400",
                        "06. volume": "321988",
                        "07. latest trading day": "2019-11-27",
                        "08. previous close": "1313.0000",
                        "09. change": "-1.9600",
                        "10. change percent": "-0.1493%",
                    },
                    "symbol": "GOOGL",
                },
                {
                    "alias": "Samsung Electronics",
                    "data": {
                        "01. symbol": "005930.KS",
                        "02. open": "51800.0000",
                        "03. high": "52300.0000",
                        "04. low": "51600.0000",
                        "05. price": "52200.0000",
                        "06. volume": "7186737",
                        "07. latest trading day": "2019-11-27",
                        "08. previous close": "51800.0000",
                        "09. change": "400.0000",
                        "10. change percent": "0.7722%",
                    },
                    "symbol": "005930.KS",
                },
            ],
        },
    )


class ExceptionUndefined(Undefined):
    """Raises an UndefinedError if a jinja variable used in a template is not defined"""

    def __str__(self):
        raise UndefinedError(f"Variable '{self._undefined_name}' is not defined")


@pytest.fixture(scope="function")
def mock_env(monkeypatch):
    # Use the test-settings file for the mocked flask app, but patch the database path
    monkeypatch.setenv(
        "FLIRROR_SETTINGS", os.path.join(FIXTURE_DIR, "test-settings.cfg")
    )

    # TODO Which database will be used here


@pytest.fixture(scope="function")
def mock_app(mock_env, tmpdir_factory):
    # NOTE (felix): We are using the tmpdir_factory rather than tmpdir to allow
    # this fixture be defined on a session scope.

    # Use the test-settings file for the mocked flask app, but patch the database path
    config = {"DATABASE_FILE": str(tmpdir_factory.mktemp("data").join("test.db"))}

    # Overwrite the jinja options to make template rendering fail on undefined variables
    jinja_options = {"undefined": ExceptionUndefined}

    app = create_web(config, jinja_options)
    app.debug = True

    # Populate the database with mocked values (similar to what the run-backstop.py
    # script does).
    populate_database(app.extensions["database"])

    return app.test_client()
