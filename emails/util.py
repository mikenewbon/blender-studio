"""Utilities for rendering email templates."""
from typing import Dict, Optional
import logging

from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _get_site_url():
    domain = get_current_site(None).domain
    return f'https://{domain}'


def absolute_url(
    view_name: str, args: Optional[tuple] = None, kwargs: Optional[dict] = None
) -> str:
    """Same as django.urls.reverse() but then as absolute URL.

    For simplicity this assumes HTTPS is used.
    """
    from urllib.parse import urljoin

    relative_url = reverse(view_name, args=args, kwargs=kwargs)
    return urljoin(_get_site_url(), relative_url)


def is_noreply(email: str) -> bool:
    """Return True if the email address is a no-reply address."""
    return email.startswith('noreply@') or email.startswith('no-reply@')


def get_template_context() -> Dict[str, str]:
    """Return additional context for use in an email template."""
    return {
        'site_url': _get_site_url(),
        'billing_url': absolute_url('user-settings-billing'),
    }
