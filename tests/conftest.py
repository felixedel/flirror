import os

import pytest

from flirror.database import create_database_and_entities

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "testdata")


@pytest.fixture(scope="function")
def mock_google_env(monkeypatch):
    monkeypatch.setenv(
        "GOOGLE_OAUTH_CLIENT_SECRET", os.path.join(FIXTURE_DIR, "client_secret.json")
    )


@pytest.fixture(scope="function")
def mock_database(tmpdir):
    database_file = os.path.join(tmpdir, "test_database.sqlite")
    db = create_database_and_entities(
        provider="sqlite", filename=database_file, create_db=True
    )
    yield db
    db.disconnect()
