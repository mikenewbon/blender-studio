"""Mailgun API calls."""
from typing import Optional, Dict, List, Union
from urllib.parse import quote as urlquote
import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
import requests

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
BASE_URL = 'https://api.mailgun.net/v3'
DOMAIN_URL = f'{BASE_URL}/{settings.MAILGUN_SENDER_DOMAIN}'
UNSUBSCRIBES_URL = f'{DOMAIN_URL}/unsubscribes'


def _request_mailgun(url: str, method='GET', **kwargs) -> Optional[Dict]:
    logger.warning(f'--> [{method}] {url} with {kwargs}')
    response = requests.request(
        method=method,
        url=url,
        auth=('api', settings.MAILGUN_API_KEY),
        **kwargs,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code != 404:
            logger.exception(
                'Request to Mailgun API failed: %s, %s', response.status_code, response.text
            )
    logger.debug(f'<-- [{method} {response.status_code}] {url} {response.content}')
    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        return response.content
    except Exception:
        raise


def get_unsubscribe_record(email: str) -> Optional[Dict]:
    """Fetch a single unsubscribe record."""
    url = f'{UNSUBSCRIBES_URL}/{urlquote(email)}'
    return _request_mailgun(url)


def create_unsubscribe_record(*emails: List[str]) -> Optional[Dict]:
    """Add an address to the unsubscribe list."""
    return _request_mailgun(
        UNSUBSCRIBES_URL, method='POST', json=[{'address': email} for email in emails]
    )


def delete_unsubscribe_record(email: str):
    """Remove an address from the unsubscribes list."""
    url = f'{UNSUBSCRIBES_URL}/{urlquote(email)}'
    return _request_mailgun(url, method='DELETE')


def add_to_maillist(alias_address: str, users: Union[List[User], QuerySet]) -> Optional[Dict]:
    """Add given user to a mailing list with a given alias address."""
    url = f'{BASE_URL}/lists/{urlquote(alias_address)}/members.json'
    return _request_mailgun(
        url,
        method='POST',
        data={
            'upsert': True,
            # The endpoint doesn't accept application/json with "members", it accepts
            # "members" as JSON-encoded string instead.
            'members': json.dumps(
                [
                    {
                        'address': user.email,
                        'name': user.profile.full_name,
                        'subscribed': user.profile.is_subscribed_to_newsletter,
                    }
                    for user in users
                ]
            ),
        },
    )


def delete_from_maillist(alias_address: str, email: str) -> Optional[Dict]:
    """Delete a given user from a mailing list with a given alias address."""
    url = f'{BASE_URL}/lists/{urlquote(alias_address)}/members/{urlquote(email)}'
    return _request_mailgun(url, method='DELETE')
