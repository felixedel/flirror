import logging
import os
import time

import google.oauth2.credentials
import requests
from google_auth_oauthlib.flow import Flow

from flirror.database import get_object_by_key, store_object_by_key
from flirror.exceptions import GoogleOAuthError

LOGGER = logging.getLogger(__name__)


class GoogleOAuth:

    GOOGLE_OAUTH_ACCESS_URL = "https://accounts.google.com/o/oauth2/device/code"
    GOOGLE_OAUTH_POLL_URL = "https://www.googleapis.com/oauth2/v4/token"

    # We could use the class object to store the active token in the session
    # and check this one first for expiry, before retrieving a new one and store
    # that in the database and session.
    def __init__(self, scopes=None):
        if scopes is None:
            scopes = []
        self.scopes = scopes

    def get_credentials(self):
        token = self.authenticate()
        if token is None:
            LOGGER.warning("Authentication failed. Cannot retrieve calendar data")
            return

        flow = self._get_oauth_flow()
        # TODO To let google refresh the token, we must specify the
        #  refresh_token and the token_uri (which we don't have in this OAuth flow).
        credentials = google.oauth2.credentials.Credentials(
            client_id=flow.client_config["client_id"],
            client_secret=flow.client_config["client_secret"],
            token=token,
        )

        return credentials

    def authenticate(self):
        LOGGER.debug("Authenticating to Google calendar API")
        # Check if we already have a valid token
        LOGGER.debug("Check if we already have an access token")

        # The most common case is to refresh an existing token, so there should
        # already be an existing database entry that we can update
        token_obj = get_object_by_key("google_oauth_token")
        if token_obj is None:
            LOGGER.debug("Could not find any access token. Requesting an initial one.")
            token = self.ask_for_access()
        else:
            now = time.time()
            if token_obj["expires_in"] <= now:
                LOGGER.debug(
                    "Found an access token, but expired. Requesting a new one."
                )
                # We use the refresh_token to get a new access token
                token = self.refresh_access_token(token_obj["refresh_token"])
            else:
                token = token_obj["access_token"]

        # Hopefully, we got a token in any case now
        return token

    def refresh_access_token(self, refresh_token):
        LOGGER.debug("Requesting a new access token using the last refresh token")
        # Use the refresh token to request a new access token
        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        now = time.time()
        res = requests.post(self.GOOGLE_OAUTH_POLL_URL, data=data)
        LOGGER.info(res.status_code)
        LOGGER.info(res.content)

        # TODO Error handling (e.g. offline)?
        token_data = res.json()
        # Calculate an absolute expiry timestamp for simpler evaluation
        token_data["expires_in"] += now

        # Only the inital access token provides the refresh token.
        # Whenever we use the refresh token to request a new access token,
        # those tokens come without another refresh token.
        if "refresh_token" not in token_data:
            token_data["refresh_token"] = refresh_token

        self._store_access_token(token_data)
        return token_data["access_token"]

    def ask_for_access(self):
        # As the device code is only necessary for the initial token request,
        # we should do both in one go. Otherwise, there are too many edge cases
        # to cover and if something goes wrong or the user does not grant us
        # permission before the device code is expired, we have to start from
        # the beginning.

        # Store current timestamp to calculate an absolute expiry date
        now = time.time()

        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "scope": " ".join(self.scopes),
        }

        res = requests.post(self.GOOGLE_OAUTH_ACCESS_URL, data=data)
        LOGGER.info(res.status_code)
        LOGGER.info(res.content)

        # TODO Error handling (e.g. offline)?
        device = res.json()
        # Calculate an absolute expiry timestamp for simpler evaluation
        device["expires_in"] += now

        LOGGER.info(
            "Please visit '%s' and enter '%s'",
            device["verification_url"],
            device["user_code"],
        )
        # TODO Show a QR code pointing to the URL + entering the code

        # TODO Poll google's auth server in the specified interval until
        #  a) the user has granted us permission and we get a valid access token
        #  b) The device code got expired (or another time out from our side)

        token_data = self.poll_for_initial_access_token(device)
        return token_data["access_token"]

    def poll_for_initial_access_token(self, device):
        # TODO Timeout, max_retries?
        # Theoretically, we can poll until the device code is expired (which is
        # 30 minutes)
        while time.time() < device["expires_in"]:
            try:
                now = time.time()
                token_data = self._request_initial_access_token(device)
                # Calculate an absolute expiry timestamp for simpler evaluation
                token_data["expires_in"] += now
                self._store_access_token(token_data)
                return token_data
            except requests.exceptions.HTTPError as e:
                LOGGER.error(
                    "Could not get initial access token. You might want "
                    "to grant us permission first: %s",
                    e,
                )
                # Should be around 5 secs
                time.sleep(device["interval"])
        raise GoogleOAuthError("Device is expired, please restart the application.")

    def _request_initial_access_token(self, device):
        # Use the device code for an initial token request
        flow = self._get_oauth_flow()
        data = {
            "client_id": flow.client_config["client_id"],
            "client_secret": flow.client_config["client_secret"],
            "code": device["device_code"],
            "grant_type": "http://oauth.net/grant_type/device/1.0",
        }
        res = requests.post(self.GOOGLE_OAUTH_POLL_URL, data=data)
        # We catch this in the caller method
        res.raise_for_status()

        return res.json()

    @staticmethod
    def _store_access_token(token_data):
        store_object_by_key(key="google_oauth_token", value=token_data)

    def _get_oauth_flow(self):
        client_secret_file = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        if client_secret_file is None:
            raise GoogleOAuthError(
                "Environment variable 'GOOGLE_OAUTH_CLIENT_SECRET' "
                "must be set and point to a valid client-secret.json file"
            )

        # Let the flow creation parse the client_secret file
        try:
            flow = Flow.from_client_secrets_file(client_secret_file, scopes=self.scopes)
        except FileNotFoundError:
            raise GoogleOAuthError(
                "Could not load Google OAuth flow from '{}'. "
                "Are you sure this file exists?".format(client_secret_file)
            )
        return flow
