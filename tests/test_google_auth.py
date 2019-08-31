import os
import time
from unittest import mock

import pytest
import requests
import requests_mock
from freezegun import freeze_time

from flirror.crawler.google_auth import GoogleOAuth
from flirror.database import get_object_by_key, store_object_by_key
from flirror.exceptions import GoogleOAuthError


def test_get_credentials(mock_google_env):
    goauth = GoogleOAuth(database=None)
    with mock.patch.object(goauth, "authenticate", return_value="patched_access_token"):
        credentials = goauth.get_credentials()

    assert credentials.client_id == "test_client_id"
    assert credentials.client_secret == "test_client_secret"
    assert credentials.token == "patched_access_token"


def test_get_credentials_failed(mock_google_env):
    goauth = GoogleOAuth(database=None)
    with mock.patch.object(goauth, "authenticate", return_value=None):
        credentials = goauth.get_credentials()

    assert credentials is None


def test_authenticate_no_existing_token(mock_google_env, mock_database):
    goauth = GoogleOAuth(database=mock_database)
    with mock.patch.object(goauth, "ask_for_access", return_value="new_access_token"):
        token = goauth.authenticate()

    assert token == "new_access_token"


@freeze_time("2019-08-21 00:00:00")
def test_authenticate_expired_token(mock_google_env, mock_database):
    goauth = GoogleOAuth(database=mock_database)
    expired_token_data = {
        "access_token": "expired_access_token",
        "expires_in": time.time() - 3600,
        "refresh_token": "refresh_token",
    }
    # Store expired token in database, so it will be found in the authentication process
    store_object_by_key(mock_database, "google_oauth_token", expired_token_data)

    with mock.patch.object(
        goauth, "refresh_access_token", return_value="new_access_token"
    ):
        token = goauth.authenticate()

    assert token == "new_access_token"


def test_authenticate_valid_token(mock_google_env, mock_database):
    goauth = GoogleOAuth(database=mock_database)
    valid_token_data = {
        "access_token": "valid_access_token",
        "expires_in": time.time() + 3600,
        "refresh_token": "refresh_token",
    }

    # Store valid token in database, so it will be found in the authentication process
    store_object_by_key(mock_database, "google_oauth_token", valid_token_data)

    token = goauth.authenticate()
    assert token == "valid_access_token"


@freeze_time("2019-08-21 00:00:00")
def test_refresh_access_token(mock_google_env, mock_database):
    goauth = GoogleOAuth(database=mock_database)
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
        stored_token = get_object_by_key(mock_database, "google_oauth_token")
        assert stored_token == {
            "access_token": "some_access_token",
            "expires_in": time.time() + 3600,
            "refresh_token": "refresh_token",
            "scope": "https://www.googleapis.com/auth/calendar.readonly",
            "token_type": "Bearer",
        }


def test_ask_for_access(mock_google_env):
    goauth = GoogleOAuth(database=None)

    device = {
        "device_code": "device_code",
        "verification_url": "some-google-device-url",
        "expires_in": 3600,
        "user_code": "ABCD-EFGH",
    }

    token_data = {"access_token": "new_access_token"}

    with requests_mock.mock() as m, mock.patch.object(
        goauth, "poll_for_initial_access_token", return_value=token_data
    ):
        m.post(goauth.GOOGLE_OAUTH_ACCESS_URL, json=device)

        token = goauth.ask_for_access()

        assert token == "new_access_token"


def test_request_initial_access_token(mock_google_env):
    goauth = GoogleOAuth(database=None)

    device = {
        "device_code": "device_code",
        "verification_url": "some-google-device-url",
        "expires_in": 3600,
        "user_code": "ABCD-EFGH",
    }

    expected_data = {
        "access_token": "initial_access_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600,
        # TODO (felix): What else?
        "token_type": "Bearer",
    }

    with requests_mock.mock() as m:
        m.post(goauth.GOOGLE_OAUTH_POLL_URL, json=expected_data)

        token_data = goauth._request_initial_access_token(device)
        assert token_data == expected_data


@freeze_time("2019-08-21 00:00:00")
def test_poll_for_initial_access_token(mock_google_env, mock_database):
    goauth = GoogleOAuth(database=mock_database)

    device = {
        "device_code": "device_code",
        "verification_url": "some-google-device-url",
        "expires_in": time.time() + 3600,
        "user_code": "ABCD-EFGH",
    }

    with mock.patch.object(
        goauth, "_request_initial_access_token", return_value={"expires_in": 3600}
    ):
        token_data = goauth.poll_for_initial_access_token(device)
    assert token_data == {"expires_in": time.time() + 3600}


@freeze_time("2019-08-21 00:00:00")
def test_poll_for_initial_access_token_expired(mock_google_env):
    goauth = GoogleOAuth(database=None)

    device = {"expires_in": time.time() - 3600}

    with pytest.raises(GoogleOAuthError) as excinfo:
        goauth.poll_for_initial_access_token(device)

    assert "Device is expired, please restart the application." == str(excinfo.value)


@freeze_time("2019-08-21 00:00:00")
def test_poll_for_initial_access_token_retry(mock_google_env, mock_database):
    # TODO Release and recreate database connection between tests
    goauth = GoogleOAuth(database=mock_database)

    # Mock the device with a 0 interval, so we don't actively wait between the calls
    # in this test.
    device = {"expires_in": time.time() + 3600, "interval": 0}

    side_effects = [
        requests.exceptions.HTTPError,
        requests.exceptions.HTTPError,
        {"expires_in": 3600},
    ]

    # Mock the first two responses to return errors, on the third call we will
    # get a result
    with mock.patch.object(
        goauth, "_request_initial_access_token", side_effect=side_effects
    ) as req_mock:
        goauth.poll_for_initial_access_token(device)

    # Ensure that the req_mock method was called three times (two failures, one success)
    # with the actual device parameters
    assert req_mock.call_args_list == [
        mock.call(device),
        mock.call(device),
        mock.call(device),
    ]

    # TODO Provide the db object for the get_object_by_key lookup

    # Ensure that the token was stored in the database with the correct
    # expiration time relative to when the token was stored.
    stored_token = get_object_by_key(mock_database, "google_oauth_token")
    # TODO Validate that the expires_in is "increased" due to the retries? E.g. with
    # freezegun's auto_tick_seconds.
    assert stored_token == {"expires_in": time.time() + 3600}


def test_get_oauth_flow(mock_google_env):
    goauth = GoogleOAuth(database=None)

    flow = goauth._get_oauth_flow()
    assert flow.client_config["client_id"] == "test_client_id"
    assert flow.client_config["client_secret"] == "test_client_secret"


def test_get_oauth_flow_missing():
    goauth = GoogleOAuth(database=None)

    # Ensure that a exception is raised because no GOOGLE_OAUTH_CLIENT_SECRET
    # envvar is set
    with pytest.raises(GoogleOAuthError) as excinfo:
        goauth._get_oauth_flow()
    assert (
        "Environment variable 'GOOGLE_OAUTH_CLIENT_SECRET' must be set "
        "and point to a valid client-secret.json file"
    ) == str(excinfo.value)


def test_get_oauth_flow_invalid():
    goauth = GoogleOAuth(database=None)

    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "invalid_client_secret_file"

    with pytest.raises(GoogleOAuthError) as excinfo:
        goauth._get_oauth_flow()

    assert (
        "Could not load Google OAuth flow from 'invalid_client_secret_file'. "
        "Are you sure this file exists?"
    ) == str(excinfo.value)
