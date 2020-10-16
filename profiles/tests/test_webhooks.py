from typing import Dict, Union
from unittest.mock import patch
import hashlib
import hmac
import json
import responses

from django.contrib.auth.models import User, Group
from django.test import TestCase, override_settings
from django.urls import reverse

from common.tests.factories.users import UserFactory
from profiles.models import Profile
import profiles.tests.util as util

BLENDER_ID_BASE_URL = 'http://id.local:8000/'


def prepare_hmac_header(body: Union[str, dict], secret: str = 'testsecret') -> Dict[str, str]:
    """Return a dict containing an HMAC header matching a given request body."""
    if isinstance(body, dict):
        body = json.dumps(body).encode()

    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return {'HTTP_X-Webhook-HMAC': mac.hexdigest()}


@override_settings(
    BLENDER_ID={
        'BASE_URL': BLENDER_ID_BASE_URL,
        'OAUTH_CLIENT': 'testoauthclient',
        'OAUTH_SECRET': 'testoathsecret',
        'WEBHOOK_USER_MODIFIED_SECRET': b'testsecret',
    }
)
class WebhooksTest(TestCase):
    webhook_payload = {
        'avatar_changed': False,
        'email': 'newmail@example.com',
        'full_name': 'Иван Васильевич Doe',
        'id': 2,
        'old_email': 'mail@example.com',
        'roles': [],
    }

    def setUp(self):
        self.url = reverse('webhook-user-modified')
        util.mock_blender_id_responses()

        # Prepare a user
        self.user = UserFactory(
            email='mail@example.com',
            oauth_info__oauth_user_id='2',
            oauth_tokens__oauth_user_id='2',
            oauth_tokens__access_token='testaccesstoken',
            oauth_tokens__refresh_token='testrefreshtoken',
        )

    def test_user_modified_missing_hmac(self):
        response = self.client.post(self.url, {}, content_type='application/json')

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'Invalid HMAC')

    def test_user_modified_invalid_hmac(self):
        url = reverse('webhook-user-modified')
        headers = {'HTTP_X-Webhook-HMAC': 'deadbeef'}
        response = self.client.post(url, {}, content_type='application/json', **headers)

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'Invalid HMAC')

    @patch('profiles.views.webhooks.WEBHOOK_MAX_BODY_SIZE', 1)
    def test_user_modified_request_body_too_large(self):
        body = {"deadbeef": "foobar"}
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEquals(response.status_code, 413)

    def test_user_modified_unexpected_content_type(self):
        response = self.client.post(
            self.url, 'text', content_type='text/plain', **prepare_hmac_header(b'text')
        )

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'Unsupported Content-Type')

    def test_user_modified_malformed_json(self):
        body = b'{"":"",}'
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'Malformed JSON')

    @responses.activate
    def test_user_modified_updates_profile_and_user(self):
        body = self.webhook_payload
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEquals(response.status_code, 204)
        self.assertEquals(response.content, b'')
        profile = Profile.objects.get(user_id=self.user.pk)
        self.assertEquals(profile.full_name, 'Иван Васильевич Doe')
        self.assertEquals(profile.user.email, 'newmail@example.com')

    @responses.activate
    def test_user_modified_avatar_changed(self):
        body = {
            **self.webhook_payload,
            'avatar_changed': True,
        }

        with self.assertLogs('profiles.models', level='INFO') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(logs.output[0], 'Avatar updated for Profile ⅉanedoe')

        self.assertEquals(response.status_code, 204)
        self.assertEquals(response.content, b'')
        profile = Profile.objects.get(user_id=self.user.pk)
        self.assertTrue(profile.avatar.name.endswith('.jpg'))

    @responses.activate
    def test_user_modified_roles_added_removed_adds_removes_user_groups(self):
        # No groups ("roles") assigned yet
        self.assertEquals(list(self.user.groups.all()), [])

        # Two new roles added
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription', 'cloud_subscriber'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEquals(response.status_code, 204)
        self.assertEquals(response.content, b'')
        user = User.objects.get(pk=self.user.pk)
        self.assertEquals(
            sorted([g.name for g in user.groups.all()]), ['has_subscription', 'subscriber'],
        )

        # One role removed
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEquals(response.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEquals(
            sorted([g.name for g in user.groups.all()]), ['has_subscription',],
        )
        # Check that the group itself still exists
        self.assertEquals(Group.objects.filter(name='subscriber').count(), 1)

        # Two roles added, one already exists
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription', 'cloud_subscriber', 'dev_core'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEquals(response.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEquals(
            sorted([g.name for g in user.groups.all()]),
            ['dev_core', 'has_subscription', 'subscriber',],
        )

    def test_user_modified_missing_oauth_info(self):
        body = {
            **self.webhook_payload,
            'id': '999',
        }
        with self.assertLogs('profiles.views.webhooks', level='ERROR') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(
                logs.output[0], 'Cannot update profile: no OAuth info found for ID 999'
            )

        self.assertEquals(response.status_code, 204)

    @responses.activate
    def test_user_modified_logs_errors_when_blender_id_user_info_broken(self):
        body = self.webhook_payload
        # Mock a "broken" user info response
        responses.replace(
            responses.GET, f'{BLENDER_ID_BASE_URL}api/me', status=403, body='Unauthorized'
        )

        with self.assertLogs('profiles.views.webhooks', level='ERROR') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(logs.output[0], 'Unable to update username for Profile')

        self.assertEquals(response.status_code, 204)

    @responses.activate
    def test_user_modified_logs_error_when_blender_id_avatar_broken(self):
        body = {
            **self.webhook_payload,
            'avatar_changed': True,
        }
        # Mock a "broken" avatar response
        responses.replace(
            responses.GET,
            f'{BLENDER_ID_BASE_URL}api/user/2/avatar',
            status=500,
            body='Houston, we have a problem',
        )

        with self.assertLogs('profiles.models', level='ERROR') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(
                logs.output[0], 'Failed to retrieve an avatar for Profile ⅉanedoe from Blender ID'
            )

        self.assertEquals(response.status_code, 204)
