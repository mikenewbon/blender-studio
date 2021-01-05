"""Implement integration with Blender ID: handling of OAuth2 session, fetching user info etc."""
from typing import Dict, Any, Tuple
from requests_oauthlib import OAuth2Session
from urllib.parse import urljoin, urlparse
import io
import logging
import pathlib

import botocore
import requests

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken
from blender_id_oauth_client.views import blender_id_oauth_settings

logger = logging.getLogger(__name__)


class BIDMissingAccessToken(Exception):
    """Raise when user accesss token is not found in DB."""


class BIDSession:
    """Wrap up interactions with Blender ID, such as fetching user info and avatar."""

    _anonymous_session = None

    def __init__(self):
        """Initialise Blender ID client settings."""
        self.settings = blender_id_oauth_settings()

    def _make_session(self, access_token: str = None) -> OAuth2Session:
        """Return a new OAuth2 session, optionally authenticated with an access token."""
        if access_token:
            return OAuth2Session(self.settings.client, token={'access_token': access_token})
        return OAuth2Session(self.settings.client)

    @property
    def session(self):
        """
        Return a reusable "anonymous" OAuth2Session for fetching avatars from Blender ID.

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
            raise BIDMissingAccessToken(f'No access token found for {oauth_user_id}')
        session = self._make_session(access_token=token.access_token)
        resp = session.get(self.settings.url_userinfo)
        resp.raise_for_status()
        payload = resp.json()
        assert isinstance(payload, dict)

        return payload

    def get_avatar_url(self, oauth_user_id: str) -> str:
        """Return a Blender ID URL to the avatar for a given OAuth ID."""
        return urljoin(self.settings.url_base, f'api/user/{oauth_user_id}/avatar')

    def get_avatar(self, oauth_user_id: str) -> Tuple[str, io.BytesIO]:
        """Retrieve an avatar from Blender ID service using an OAuth2 session.

        Return file name and content of an avatar for the given 'oauth_user_id'.
        """
        resp = self.session.get(self.get_avatar_url(oauth_user_id))
        resp.raise_for_status()

        name = pathlib.Path(urlparse(resp.url).path).name
        return name, io.BytesIO(resp.content)

    def copy_avatar_from_blender_id(self, user):
        """
        Attempt to retrieve an avatar from Blender ID and save it into our storage.

        If either OAuth info or Blender ID service isn't available, log an error and return.
        """
        if not hasattr(user, 'oauth_info'):
            logger.warning(f'Cannot copy avatar from Blender ID: {user} is missing OAuth info')
            return
        oauth_info = user.oauth_info
        try:
            name, content = self.get_avatar(oauth_info.oauth_user_id)
            if user.image:
                # Delete the previous file
                user.image.delete(save=False)
            user.image.save(name, content, save=True)
            logger.info(f'Profile image updated for {user}')
        except requests.HTTPError:
            logger.exception(f'Failed to retrieve an image for {user} from Blender ID')
        except botocore.exceptions.BotoCoreError:
            logger.exception(f'Failed to store an image for {user}')
        except Exception:
            logger.exception(f'Failed to copy an image for {user}')

    def update_username(self, user, oauth_user_id):
        """Update username of a given user, fetching it from Blender ID.

        FIXME(anna): webhook payload doesn't include username, hence this separate method.
        """
        try:
            user_info = self.get_user_info(oauth_user_id)
            if user_info['nickname'] != user.username:
                # TODO(anna) handle duplicate usernames
                user.username = user_info['nickname']
                user.save(update_fields=['username'])
        except BIDMissingAccessToken:
            logger.warning(f'Unable to retrieve username for {user}: no access token')
        except Exception:
            logger.exception(f'Unable to update username for {user}')
