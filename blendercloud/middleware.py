"""Takes care of reading Flask session and storing its data in our own Django session.

The goal of this is to allow Blender Studio pages to be run as part of Blender Cloud,
sharing login information without requiring users to login again every time they visit pages
that aren't actually served by Blender Cloud.
"""
import logging

from django.conf import settings
from django.contrib.auth import login, logout
from loginas.utils import is_impersonated_session

import blendercloud.session

logger = logging.getLogger(__name__)


class SessionMiddleware:
    """Copies login info from Blender Cloud session into current Django session."""

    def __init__(self, get_response):
        """One-time configuration and initialization."""
        self.get_response = get_response

    def __call__(self, request):
        """Copy Blender Cloud session data into current session.

        Blender Cloud fully controls the authentication, which means that if its session cookie
        is not available, user is not logged in from Django's point of view.
        This middleware can be enabled with a `settings.BLENDER_CLOUD_AUTH_ENABLED` flag.
        """
        forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
        host = request.META.get('HTTP_HOST')
        if (
            not is_impersonated_session(request)
            and settings.BLENDER_CLOUD_AUTH_ENABLED
            and (
                settings.BLENDER_CLOUD_DOMAIN is None
                or settings.BLENDER_CLOUD_DOMAIN in (host, forwarded_host)
            )
        ):
            self._modify_session(request)

        response = self.get_response(request)
        # This middleware doesn't do anything with the response
        return response

    def _modify_session(self, request):
        try:
            user = blendercloud.session.get_or_create_current_user(request)
        except Exception:
            user = None
            logger.exception('Error while reading Blender Cloud session')

        if user is not None:
            # This should be killed with fire.
            keep_csrf = request.META.get('CSRF_COOKIE')
            # **N.B**: `login()` always rotates the CSRF token!
            login(request, user)
            # Undo what `login()` does with the CSRF token, otherwise
            # CSRF verification will always be failing when this middleware is active
            if keep_csrf:
                request.META['CSRF_COOKIE'] = keep_csrf
                request.csrf_cookie_needs_reset = False
            logger.debug('Authenticated Blender Cloud user: %s', user)
        elif request.user.is_authenticated:
            logout(request)
            logger.debug('User is authenticated but Blender Cloud session is not available')
