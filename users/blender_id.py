"""Implement integration with Blender ID: handling of OAuth2 session, fetching user info etc."""
from typing import Dict, Any, Tuple
from requests_oauthlib import OAuth2Session
from urllib.parse import urljoin, urlparse
import io
import logging
import pathlib

from django.conf import settings
import botocore
import requests
import requests.exceptions

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken
from blender_id_oauth_client.views import blender_id_oauth_settings, ClientSettings

logger = logging.getLogger(__name__)


class BIDMissingAccessToken(Exception):
    """Raise when user accesss token is not found in DB."""


class BIDSession:
    """Wrap up interactions with Blender ID, such as fetching user info and avatar."""

    _anonymous_session = None
    _badger_api_session = None

    def __init__(self):
        """Initialise Blender ID client settings."""
        self.settings = blender_id_oauth_settings()

    def _make_session(self, access_token: str = None) -> OAuth2Session:
        """Return a new OAuth2 session, optionally authenticated with an access token."""
        if access_token:
            return OAuth2Session(self.settings.client, token={'access_token': access_token})
        return OAuth2Session(self.settings.client)

    @property
    def badger_oauth_settings(self) -> ClientSettings:
        """Container for badger API OAuth Client settings."""
        return ClientSettings(
            client=settings.BLENDER_ID['BADGER_API_OAUTH_CLIENT'],
            secret=settings.BLENDER_ID['BADGER_API_OAUTH_SECRET'],
            url_base=self.settings.url_base,
            url_authorize=self.settings.url_authorize,
            url_token=self.settings.url_token,
            url_userinfo=self.settings.url_userinfo,
            url_logout=self.settings.url_logout,
        )

    @property
    def session(self):
        """
        Return a reusable "anonymous" OAuth2Session for fetching avatars from Blender ID.

        Create it the first time this property is accessed.
        """
        if not self._anonymous_session:
            self._anonymous_session = self._make_session()
        return self._anonymous_session

    @property
    def badger_api_session(self):
        """
        Return a reusable OAuth2Session for granting/revoking roles with Blender ID API.

        Create it the first time this property is accessed.
        """
        if not self._badger_api_session:
            token = settings.BLENDER_ID['BADGER_API_ACCESS_TOKEN']
            self._badger_api_session = OAuth2Session(
                self.badger_oauth_settings.client, token={'access_token': token}
            )
        return self._badger_api_session

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

    def get_badges_url(self, oauth_user_id: str) -> str:
        """Return a Blender ID URL to the avatar for a given OAuth ID."""
        return urljoin(self.settings.url_base, f'api/badges/{oauth_user_id}')

    def get_user_by_id_url(self, oauth_user_id: str) -> str:
        """Return a Blender ID URL for the user with a given OAuth ID."""
        return urljoin(self.settings.url_base, f'api/user/{oauth_user_id}')

    def get_check_user_by_email_url(self, email: str) -> str:
        """Return a Blender ID URL for checking existence of a record with a given email."""
        return urljoin(self.settings.url_base, f'api/check-user/{email}')

    def get_badger_api_url(self, action: str, role: str, oauth_user_id: str) -> str:
        """Return a Blender ID API URL for granting/revoking roles."""
        assert action in ('grant', 'revoke'), f'{action} is not a known Blender ID API action'
        assert role in (
            'cloud_subscriber',
            'cloud_has_subscription',
            'sprite_fright',
        ), f'{role} is not a known Blender ID badge'
        return urljoin(self.settings.url_base, f'api/badger/{action}/{role}/{oauth_user_id}')

    def get_avatar(self, oauth_user_id: str) -> Tuple[str, io.BytesIO]:
        """Retrieve an avatar from Blender ID service using an OAuth2 session.

        Return file name and content of an avatar for the given 'oauth_user_id'.
        """
        resp = self.session.get(self.get_avatar_url(oauth_user_id))
        resp.raise_for_status()

        name = pathlib.Path(urlparse(resp.url).path).name
        return name, io.BytesIO(resp.content)

    def get_badges(self, oauth_user_id: str) -> Dict[str, Any]:
        """Retrieve badges from Blender ID service using a user-specific OAuth2 session."""
        token = self.get_oauth_token(oauth_user_id)
        if not token:
            raise BIDMissingAccessToken(f'No access token found for {oauth_user_id}')
        session = self._make_session(access_token=token.access_token)
        resp = session.get(self.get_badges_url(oauth_user_id))
        resp.raise_for_status()
        badges = resp.json().get('badges', {})
        assert isinstance(badges, dict)

        return badges

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
            logger.warning(f'Failed to retrieve an image for {user} from Blender ID')
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
        except requests.exceptions.HTTPError:
            logger.warning(f'Unable to update username for {user}: HTTPError')
        except Exception:
            logger.exception(f'Unable to update username for {user}')

    def copy_badges_from_blender_id(self, user):
        """
        Attempt to retrieve badges from Blender ID and save them in the user record.

        If either OAuth info or Blender ID service isn't available, log an error and return.
        """
        if not hasattr(user, 'oauth_info'):
            logger.warning(f'Cannot copy badges from Blender ID: {user} is missing OAuth info')
            return
        oauth_info = user.oauth_info
        try:
            badges = self.get_badges(oauth_info.oauth_user_id)
            if badges:
                user.badges = badges
                user.save(update_fields=['badges'])
            logger.info(f'Badges updated for {user}')
        except requests.HTTPError:
            logger.warning(f'Failed to retrieve badges of {user} from Blender ID')
        except BIDMissingAccessToken:
            logger.warning(f'Unable to retrieve badges for {user}: no access token')
        except Exception:
            logger.exception(f'Failed to copy an image for {user}')

    def grant_revoke_role(self, user, action: str, role: str) -> None:
        """Grant or revoke a given role (badge) to/from a user with a given OAuth ID."""
        if not hasattr(user, 'oauth_info'):
            logger.warning('Cannot %s Blender ID %s: %s is missing OAuth info', action, role, user)
            return
        oauth_info = user.oauth_info
        oauth_user_id = oauth_info.oauth_user_id
        url = self.get_badger_api_url(action=action, role=role, oauth_user_id=oauth_user_id)
        resp = self.badger_api_session.post(url)
        resp.raise_for_status()

    def get_user_by_id(self, oauth_user_id: str) -> Dict[str, str]:
        """Get Blender ID user info using the API OAuth token."""
        url = self.get_user_by_id_url(oauth_user_id=oauth_user_id)
        resp = self.badger_api_session.get(url)
        resp.raise_for_status()
        return resp.json()

    def check_user_by_email(self, email: str) -> Dict[str, str]:
        """Check if Blender ID with a given email exists."""
        url = self.get_check_user_by_email_url(email=email)
        resp = self.badger_api_session.get(url)
        resp.raise_for_status()
        return resp.json()
