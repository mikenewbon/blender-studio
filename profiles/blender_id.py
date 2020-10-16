"""Implement integration with Blender ID: handling of OAuth2 session, fetching user info etc."""
from typing import Dict, Any, Tuple
from requests_oauthlib import OAuth2Session
from urllib.parse import urlparse, urljoin
import pathlib
import io
import logging

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken
from blender_id_oauth_client.views import blender_id_oauth_settings

logger = logging.getLogger(__name__)


class BIDSession:
    """Wrap up interactions with Blender ID, such as fetching user info and avatar."""

    _anonymous_session = None

    def __init__(self):
        """Initialise Blender ID client settings."""
        self.settings = blender_id_oauth_settings()

    def _make_session(self, access_token: str = None) -> OAuth2Session:
        """Return a new OAuth2 session, optionally authenticated with an access token."""
        if access_token:
            return OAuth2Session(self.settings.client, token={'access_token': access_token,},)
        return OAuth2Session(self.settings.client)

    @property
    def session(self):
        """Return a reusable "anonymous" OAuth2Session for fetching avatars from Blender ID.

        Create it the first time this property is accessed.
        """
        if not self._anonymous_session:
            self._anonymous_session = self._make_session()
        return self._anonymous_session

    @classmethod
    def get_oauth_user_info(cls, oauth_user_id: str) -> OAuthUserInfo:
        """Return OAuthUserInfo record for a given Blender ID.

        Used primarily to look up our own user ID associated with an external Blender ID,
        for example in the user modified webhook.
        """
        return (
            OAuthUserInfo.objects.select_related('user')
            .prefetch_related('user__groups')
            .get(oauth_user_id=oauth_user_id)
        )

    @classmethod
    def get_oauth_token(cls, oauth_user_id: str) -> OAuthToken:
        """Return OAuthToken for a given ID to be used in authenticated requests to Blender ID."""
        return OAuthToken.objects.filter(oauth_user_id=oauth_user_id).last()

    def get_user_info(self, oauth_user_id: str) -> Dict[str, Any]:
        """Retrieve user info from Blender ID service using a user-specific OAuth2 session.

        User info is returned in the following format:
        {
            "id": 2,
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "nickname": "janedoe",
            "roles": {"dev_core": True},
        }
        """
        token = self.get_oauth_token(oauth_user_id)
        if not token:
            raise Exception(f'No access token found for {oauth_user_id}')
        session = self._make_session(access_token=token.access_token)
        resp = session.get(self.settings.url_userinfo)
        resp.raise_for_status()
        payload = resp.json()
        assert isinstance(payload, dict)

        return payload

    def get_avatar(self, oauth_user_id: str) -> Tuple[str, io.BytesIO]:
        """Retrieve an avatar from Blender ID service using an OAuth2 session.

        Return file name and content of an avatar for the given 'oauth_user_id'.
        """
        resp = self.session.get(urljoin(self.settings.url_base, f'api/user/{oauth_user_id}/avatar'))
        resp.raise_for_status()

        name = pathlib.Path(urlparse(resp.url).path).name
        return name, io.BytesIO(resp.content)
