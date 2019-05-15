import os

import flask
from flask import current_app
from google_auth_oauthlib.flow import Flow

from .views import FlirrorMethodView


# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


# Adapted example from
# https://developers.google.com/api-client-library/python/auth/web-app
class OAuth2View(FlirrorMethodView):

    endpoint = "oauth2"
    rule = "/oauth2"
    template_name = None

    def get(self):
        client_secret_file = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        if client_secret_file is None:
            current_app.logger.warning(
                "Environment variable 'GOOGLE_OAUTH_CLIENT_SECRET' "
                "must be set and point to a valid client-secret.json file"
            )
            return

        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps
        flow = Flow.from_client_secrets_file(client_secret_file, scopes=SCOPES)

        flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh the access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type="offline",
            # Enable incremental authorization, Recommended as best practice.
            include_granted_scopes="true",
        )

        # Store the state so the callback can verify the auth server response
        flask.session["oauth2_state"] = state

        # TODO (felix): Hack to allow oauth token transport without https
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        return flask.redirect(authorization_url)


class OAuth2CallbackView(FlirrorMethodView):

    endpoint = "oauth2callback"
    rule = "/oauth2callback"
    template_name = None

    def get(self):
        client_secret_file = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        if client_secret_file is None:
            current_app.logger.warning(
                "Environment variable 'GOOGLE_OAUTH_CLIENT_SECRET' "
                "must be set and point to a valid client-secret.json file"
            )
            return

        # Specify the state when creating the flow in the callback so that it can
        # be verified in the authorization server response
        state = flask.session["oauth2_state"]

        # TODO (felix): Provide the scopes in the original request
        flow = Flow.from_client_secrets_file(
            client_secret_file, scopes=SCOPES, state=state
        )
        flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

        # Use the authorization server's response to fetch the OAuth 2.0 tokens
        authorization_response = flask.request.url
        flow.fetch_token(authorization_response=authorization_response)

        # Store credentials in the session
        # TODO (felix): Store that somewhere else (sqlite?), so we don't need
        #  to retrieve them again after every restart.
        credentials = flow.credentials
        flask.session["oauth2_credentials"] = self._credentials_to_dict(credentials)

        # TODO (felix): Provide the target endpoint in the original request
        return flask.redirect(flask.url_for("calendar"))

    @staticmethod
    def _credentials_to_dict(creds):
        return {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
