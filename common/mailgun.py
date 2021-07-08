"""Mailgun API calls."""
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote as urlquote
import json
import logging

from django.conf import settings
import requests

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
BASE_URL = 'https://api.mailgun.net/v3'
DOMAIN_URL = f'{BASE_URL}/{settings.MAILGUN_SENDER_DOMAIN}'
UNSUBSCRIBES_URL = f'{DOMAIN_URL}/unsubscribes'


def _request_mailgun(url: str, method='GET', **kwargs) -> Optional[Dict]:
    if not getattr(settings, 'MAILGUN_API_KEY', None):
        logger.error('MAILGUN_API_KEY is missing')
        return

    logger.debug(f'--> [{method}] {url} with {kwargs}')
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


def add_to_maillist(alias_address: str, recipients: List[Tuple[str]]) -> Optional[Dict]:
    """Add given list of recipients to a mailing list with a given alias address.

    The `recipients` is expected to contain tuples of `(email, full_name)`.
    """
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
                        'address': email,
                        'name': full_name,
                        'subscribed': True,
                    }
                    for email, full_name in recipients
                ]
            ),
        },
    )


def get_from_maillist(alias_address: str, email: str) -> Optional[Dict]:
    """Retrieve a mailing list member.."""
    url = f'{BASE_URL}/lists/{urlquote(alias_address)}/members/{urlquote(email)}'
    return _request_mailgun(url, method='GET')


def delete_from_maillist(alias_address: str, email: str) -> Optional[Dict]:
    """Delete a given email from a mailing list with a given alias address."""
    url = f'{BASE_URL}/lists/{urlquote(alias_address)}/members/{urlquote(email)}'
    return _request_mailgun(url, method='DELETE')


def download_maillist(alias_address: str, limit: int = 100) -> List[Tuple[str]]:
    """Retrieve the full mailing list and write it down as a CSV."""
    result = []
    page_url = f'{BASE_URL}/lists/{urlquote(alias_address)}/members/pages?page=first&limit={limit}'
    page = _request_mailgun(page_url, method='GET')
    while page and page.get('items'):
        result.extend([(_['name'], _['address']) for _ in page['items']])
        page_url = page.get('paging', {}).get('next')
        page = _request_mailgun(page_url, method='GET')
    with open(f'mailgun_{alias_address}.csv', 'w+') as f:
        for _ in result:
            f.write(f'{_[0]}, {_[1]}\n')
    return result


def download_events(**params) -> List[Dict]:
    """Retrieve all events of given type."""
    result = []
    page_url = f'{DOMAIN_URL}/events'
    page = _request_mailgun(page_url, method='GET', params=params)
    while page and page.get('items'):
        result.extend(page['items'])
        page_url = page.get('paging', {}).get('next')
        page = _request_mailgun(page_url, method='GET')
    return result
