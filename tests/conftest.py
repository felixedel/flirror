import os

import pytest
from jinja2 import Undefined
from jinja2.exceptions import UndefinedError
from pony.orm import db_session

from flirror import create_app
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


class ExceptionUndefined(Undefined):
    """Raises an UndefinedError if a jinja variable used in a template is not defined"""

    def __str__(self):
        raise UndefinedError(f"Variable '{self._undefined_name}' is not defined")


@pytest.fixture(scope="session")
def mock_app(tmpdir_factory):
    # NOTE (felix): We are using the tmpdir_factory rather than tmpdir to allow
    # this fixture be defined on a session scope.

    # Use the test-settings file for the mocked flask app, but patch the database path
    os.environ["FLIRROR_SETTINGS"] = os.path.join(FIXTURE_DIR, "test-settings.cfg")
    config = {"DATABASE_FILE": str(tmpdir_factory.mktemp("data").join("test.db"))}

    # Overwrite the jinja options to make template rendering fail on undefined variables
    jinja_options = {"undefined": ExceptionUndefined}

    app = create_app(config, jinja_options)
    app.debug = True

    # Populate the database with mocked values (similar to what the run-backstop.py
    # script does).
    populate_database(app.extensions["database"])

    return app.test_client()
