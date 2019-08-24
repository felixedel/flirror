import os
import time

import pytest
import requests_mock
from freezegun import freeze_time

from flirror.crawler.google_auth import GoogleOAuth
from flirror.database import get_object_by_key
from flirror.exceptions import GoogleOAuthError


@freeze_time("2019-08-21 00:00:00")
def test_refresh_access_token(mock_google_env, mock_database):
    goauth = GoogleOAuth()
    with requests_mock.mock() as m:
        m.post(
            goauth.GOOGLE_OAUTH_POLL_URL,
            json={
                "access_token": "some_access_token",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar.readonly",
                "token_type": "Bearer",
            },
        )

        access_token = goauth.refresh_access_token("refresh_token")

        assert access_token == "some_access_token"
        # Ensure that the request parameters were build correctly
        # TODO (felix): Could we also validate the request's data attribute
        # directly, rather than the concatenated text?
        assert m.last_request.text == (
            "client_id=test_client_id"
            "&client_secret=test_client_secret"
            "&refresh_token=refresh_token"
            "&grant_type=refresh_token"
        )

        # Ensure that the token was stored in the database with the correct
        # expiration time relative to now
        stored_token = get_object_by_key("google_oauth_token")
        assert stored_token == {
            "access_token": "some_access_token",
            "expires_in": time.time() + 3600,
            "refresh_token": "refresh_token",
            "scope": "https://www.googleapis.com/auth/calendar.readonly",
            "token_type": "Bearer",
        }


def test_get_oauth_flow(mock_google_env):
    goauth = GoogleOAuth()

    flow = goauth._get_oauth_flow()
    assert flow.client_config["client_id"] == "test_client_id"
    assert flow.client_config["client_secret"] == "test_client_secret"


def test_get_oauth_flow_missing():
    goauth = GoogleOAuth()

    # Ensure that a exception is raised because no GOOGLE_OAUTH_CLIENT_SECRET
    # envvar is set
    with pytest.raises(GoogleOAuthError) as excinfo:
        goauth._get_oauth_flow()
    assert (
        "Environment variable 'GOOGLE_OAUTH_CLIENT_SECRET' must be set "
        "and point to a valid client-secret.json file"
    ) == str(excinfo.value)


def test_get_oauth_flow_invalid():
    goauth = GoogleOAuth()

    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "invalid_client_secret_file"

    with pytest.raises(GoogleOAuthError) as excinfo:
        goauth._get_oauth_flow()

    assert (
        "Could not load Google OAuth flow from 'invalid_client_secret_file'. "
        "Are you sure this file exists?"
    ) == str(excinfo.value)
