"""Copy some of the Flask-Login's remember-me cookie logic."""
from hashlib import sha512
from typing import Optional
import hmac

from django.conf import settings
from django.http.request import HttpRequest
from werkzeug.security import safe_str_cmp


def decode_cookie(cookie: str) -> Optional[str]:
    """Decode a cookie given by `encode_cookie`.

    If verification of the cookie fails, ``None`` will be implicitly returned.

    :param cookie: An encoded cookie.
    :type cookie: str
    """
    try:
        payload, digest = cookie.rsplit(u'|', 1)
        if hasattr(digest, 'decode'):
            digest = digest.decode('ascii')  # pragma: no cover
    except ValueError:
        return

    if safe_str_cmp(_cookie_digest(payload), digest):
        return payload


def _cookie_digest(payload: str) -> str:
    key = settings.BLENDER_CLOUD_SECRET_KEY
    if isinstance(key, str):
        key = key.encode('latin1')

    return hmac.new(key, payload.encode('utf-8'), sha512).hexdigest()


def open_remember_token(request: HttpRequest) -> Optional[str]:
    """Read Flask-Login remember-me cookie from the given request.

    Return blender_id_oauth_token, which is what stored in the remember_token instead of user_id.
    """
    value = request.COOKIES.get(settings.BLENDER_CLOUD_REMEMBER_COOKIE_NAME)
    if value:
        return decode_cookie(value)
