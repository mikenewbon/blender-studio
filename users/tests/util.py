import json
import re

from django.conf import settings
from django.contrib.auth import get_user_model
import responses

from common.tests.factories.users import UserFactory

User = get_user_model()


def mock_blender_id_responses() -> None:
    """Set up mock responses of Blender ID service."""
    base_url = settings.BLENDER_ID['BASE_URL']
    responses.add(
        responses.GET,
        f'{base_url}api/user/2/avatar',
        status=302,
        headers={'Location': f'{base_url}media/cache/1c/da/1cda54d605799b1f4b0dc080.jpg'},
    )
    responses.add(
        responses.GET,
        f'{base_url}api/badges/2',
        status=200,
        json={
            'user_id': 2,
            'badges': {
                'cloud_demo': {
                    'label': 'Blender Studio',
                    'description': 'Blender Studio free account',
                    'image': f'{base_url}media/badges/badge_cloud.png',
                    'image_width': 256,
                    'image_height': 256,
                },
            },
        },
    )
    responses.add(
        responses.GET,
        f'{base_url}api/me',
        json={
            'id': 2,
            'full_name': 'ⅉane ⅅoe',
            'email': 'jane@example.com',
            'nickname': 'ⅉanedoe',
            # N.B.: roles format here differs from one in user-modified webhook payload.
            'roles': {
                'dev_core': True,
                'cloud_has_subscription': True,
                'cloud_subscriber': True,
            },
        },
    )
    with open('common/static/common/images/blank-profile-pic.png', 'rb') as out:
        responses.add(
            responses.GET,
            'http://id.local:8000/media/cache/1c/da/1cda54d605799b1f4b0dc080.jpg',
            body=out,
            stream=True,
        )


def mock_blender_id_badger_badger_response(action: str, role: str, oauth_user_id: str, rsps=None):
    """Set up mock responses of Blender ID badger API."""
    base_url = settings.BLENDER_ID['BASE_URL']
    # Use default responses mock unless provided an alternative.
    # This allows controlling assert_all_requests_are_fired flag when necessary.
    rsps = rsps or responses
    rsps.add(
        rsps.POST,
        f'{base_url}api/badger/{action}/{role}/{oauth_user_id}',
        status=200,
    )


def mock_mailgun_responses() -> None:
    """Set up mock responses of Mailgun API."""
    base_url = 'https://api.mailgun.net/v3/'
    responses.add_callback(
        responses.GET,
        re.compile(f'{base_url}.*/unsubscribes/mail1%40example.com'),
        callback=lambda request: (404, {}, ''),
    )
    responses.add_callback(
        responses.DELETE,
        re.compile(f'{base_url}.*/unsubscribes/mail1%40example.com'),
        callback=lambda request: (404, {}, ''),
    )
    responses.add_callback(
        responses.GET,
        re.compile(f'{base_url}.*/unsubscribes/mail2%40example.com'),
        callback=lambda request: (
            200,
            {},
            json.dumps(
                {
                    'address': 'mail2@example.com',
                    'tags': ['*'],
                    'created_at': 'Wed, 23 Dec 2020 16:05:53 UTC',
                }
            ),
        ),
    )
    responses.add_callback(
        responses.DELETE,
        re.compile(f'{base_url}.*/unsubscribes/mail2%40example.com'),
        callback=lambda request: (
            200,
            {},
            json.dumps(
                {
                    'address': 'mail2@example.com',
                    'message': 'Unsubscribe event has been removed',
                }
            ),
        ),
    )
    responses.add_callback(
        responses.POST,
        re.compile(f'{base_url}.*/unsubscribes'),
        callback=lambda request: (200, {}, ''),
    )
    responses.add(
        responses.POST,
        f'{base_url}lists/newsletter-test%40blender.cloud/members.json',
        json={
            'list': {
                'access_level': 'readonly',
                'address': 'newsletter-test@blender.cloud',
                'created_at': 'Mon, 14 Dec 2020 15:14:27 -0000',
                'description': 'For testing newsletters in Blender Studio',
                'members_count': 5,
                'name': '',
                'reply_preference': 'sender',
            },
            'message': 'Mailing list has been updated',
            'task-id': 'fa9226b0453711eb83880242ac11000f',
        },
    )
    responses.add(
        responses.DELETE,
        f'{base_url}lists/newsletter-test%40blender.cloud/members/mail1%40example.com',
        status=200,
        json={
            'member': {'address': 'mail1@example.com'},
            'message': 'Mailing list member has been deleted',
        },
    )


def create_admin_log_user() -> User:
    """Create the admin user used for logging."""
    admin_user = UserFactory(id=1, email='admin@blender.studio', is_staff=True, is_superuser=True)
    # Reset ID sequence to avoid clashing with an already used ID 1
    UserFactory.reset_sequence(100, force=True)
    return admin_user
