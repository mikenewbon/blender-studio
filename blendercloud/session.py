"""Reads Flask session set by Blender Cloud and retrieves user info linked to it."""
from collections import namedtuple
from typing import Any, Optional, Dict
import logging
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.http.request import HttpRequest
from flask.sessions import SecureCookieSession, SecureCookieSessionInterface
import django.db.utils

import blender_id_oauth_client.models as models
import blender_id_oauth_client.signals as signals

from .flask_login import open_remember_token
from profiles.blender_id import BIDSession
from profiles.queries import set_groups_from_roles

bid = BIDSession()
logger = logging.getLogger(__name__)

# `FlaskApp` and `FlaskRequest` contain a bare minimum of attributes allowing us to use them
# instead of "real" Flask app and Flask request objects.
# The attributes were chosen based on what Flask 1.0.3's `SecureCookieSessionInterface.open_session`
# requires to work.
FlaskApp = namedtuple(
    'FlaskApp', ['session_cookie_name', 'permanent_session_lifetime', 'secret_key'],
)
app = FlaskApp(
    session_cookie_name=settings.BLENDER_CLOUD_SESSION_COOKIE_NAME,
    permanent_session_lifetime=settings.BLENDER_CLOUD_SESSION_LIFETIME,
    secret_key=settings.BLENDER_CLOUD_SECRET_KEY,
)
FlaskRequest = namedtuple('FlaskRequest', ['cookies'])
session_interface = SecureCookieSessionInterface()


def open_session(request: HttpRequest) -> SecureCookieSession:
    """Read Flask session from a session cookie in the given request."""
    flask_request = FlaskRequest(cookies=request.COOKIES)
    flask_session: SecureCookieSession = session_interface.open_session(app, flask_request)
    return flask_session


def _get_or_create_user(user_oauth: Dict[str, Any]) -> User:
    """Get or create User and OAuthUserInfo records based on given Blender ID or given email.

    This is almost an exact copy of user lookup logic from 'blender_id_oauth_client.callback_view'.
    Once Blender Studio's login is used instead of Blender Cloud's, this should be removed.
    """
    # Look up the user by OAuth ID
    oauth_user_id = user_oauth['id']
    oauth_user_email = user_oauth['email']
    oauth_user_nickname = user_oauth['nickname']

    is_username_taken = (
        User.objects.filter(username=oauth_user_nickname)
        .exclude(oauth_info__oauth_user_id=oauth_user_id)
        .exists()
    )
    try:
        user_info = models.OAuthUserInfo.objects.get(oauth_user_id=oauth_user_id)
    except models.OAuthUserInfo.DoesNotExist:
        logger.debug('User not seen before, going to search by email address.')
        if is_username_taken:
            oauth_user_nickname += '#' + uuid.uuid4().hex[5:15]
        user, created = User.objects.get_or_create(
            email=oauth_user_email,
            defaults={
                'username': oauth_user_nickname,
                'password': User.objects.make_random_password(),
            },
        )
        models.OAuthUserInfo.objects.get_or_create(
            user=user, oauth_user_id=str(oauth_user_id),
        )
        if created:
            logger.debug('User also not found by email address, created new one.')
            signals.user_created.send(sender=user, instance=user, oauth_info=user_oauth)
    else:
        # Found user_info by OAuth ID.
        user = user_info.user

    # In case this is a previously imported record, make sure the groups are set
    group_names = user_oauth.get('roles') or []
    set_groups_from_roles(user, group_names=group_names)

    # Update the user with the info we just got
    if user.email != oauth_user_email or user.username != oauth_user_nickname:
        logger.debug(f'Updating user pk={user.pk} from OAuth server')
        # N.B.: User.email has no unique constraint, it's not clear whether this is a problem or not
        # Since Blender ID is the only source of truth about profiles in Blender Studio,
        # it should probably be Blender ID's job to handle duplicate emails.
        # Otherwise, default User model should be replaced with one that enforces unique emails.
        user.email = oauth_user_email
        user.username = oauth_user_nickname if not is_username_taken else user.username
        try:
            user.save(update_fields=['email', 'username'])
        except django.db.utils.IntegrityError as e:
            if '(username)' in str(e):
                # TODO(anna): these shouldn't happen anymore, remove later
                logger.exception('Unable to update user pk=%s: duplicate username', user.pk)
            else:
                logger.exception('Unable to update user pk=%s', user.pk)
            # Reset any changes that haven't been committed as a result of this exception
            user.refresh_from_db()

    return user


def get_or_create_current_user(request: HttpRequest) -> Optional[User]:
    """Retrieve user info from Blender Cloud session cookie and Blender ID, return a User record."""
    flask_session = open_session(request)
    access_token = flask_session.get('blender_id_oauth_token', flask_session.get('user_id'))
    if not access_token:
        logger.debug('Unable to read Blender Cloud session, falling back to remember token')
        access_token = open_remember_token(request)

    if not access_token:
        logger.debug('Unable to find access token for current user')
        return None

    # Try to find existing user using the access token found in the session's payload
    # If a user exists, there's no need to call Blender ID's /me
    existing_token = models.OAuthToken.objects.filter(access_token=access_token).last()
    if existing_token and getattr(existing_token, 'user', None):
        return existing_token.user

    # Fetch user info from Blender ID using Blender Cloud's token
    # N.B.: user info can be retrieved with an access token no matter
    # which OAuth app originally initiated the authentication flow and obtained that token.
    try:
        oauth_session = bid._make_session(access_token=access_token)
        resp = oauth_session.get(bid.settings.url_userinfo)
        resp.raise_for_status()
        oauth_info = resp.json()
    except Exception:
        logger.exception('Unable to retrieve user info from Blender ID')
        return None

    oauth_user_id = oauth_info.get('id')
    if not oauth_user_id:
        logger.error('No OAuth user ID in Blender ID response')
        return None

    # Copy `blender_id_oauth_client` logic that handles oauth_info,
    # so that once Flask session is no longer needed,
    # this could be removed requiring no other changed to the code.
    user = _get_or_create_user(oauth_info)
    if not user:
        logger.warning('Unable to create a new User from oauth_info')
        return None

    # There is no refresh token or expiration available from Blender Cloud session,
    # hence only the access token is stored
    models.OAuthToken.objects.create(
        user=user, oauth_user_id=oauth_user_id, access_token=access_token,
    )
    return user
