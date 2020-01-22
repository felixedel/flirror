import os

import pytest
from jinja2 import Undefined
from jinja2.exceptions import UndefinedError

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

    return app.test_client()
