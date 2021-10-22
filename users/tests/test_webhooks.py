from typing import Dict, Union
from unittest.mock import patch, Mock
import hashlib
import hmac
import json
import responses

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings, TransactionTestCase
from django.urls import reverse
import dateutil

from common.tests.factories.users import UserFactory
import users.tests.util as util
import users.tasks as tasks
import users.views.webhooks as webhooks

User = get_user_model()
BLENDER_ID_BASE_URL = 'http://id.local:8000/'


def _mailgun_signature(timestamp, token, signing_key='test-signing-key') -> str:
    hmac_digest = hmac.new(
        key=signing_key.encode(),
        msg=('{}{}'.format(timestamp, token)).encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return str(hmac_digest)


mailgun_tracking_unsubscribed = {
    'signature': {
        'timestamp': '1608721812',
        'token': 'bf14cf81a76e8e3149750467b582f010e65ff2afc1626d3ac1',
        'signature': _mailgun_signature(
            '1608721812', 'bf14cf81a76e8e3149750467b582f010e65ff2afc1626d3ac1'
        ),
    },
    'event-data': {
        'geolocation': {'country': 'US', 'region': 'CA', 'city': 'San Francisco'},
        'tags': ['my_tag_1', 'my_tag_2'],
        'ip': '50.56.129.169',
        'recipient-domain': 'example.com',
        'event': 'UNSUBSCRIBED',
        'campaigns': [],
        'user-variables': {'my_var_1': 'Mailgun Variable #1', 'my-var-2': 'awesome'},
        'log-level': 'info',
        'timestamp': 1521243339.873676,
        'client-info': {
            'client-os': 'Linux',
            'device-type': 'desktop',
            'client-name': 'Chrome',
            'client-type': 'browser',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31',
        },
        'message': {
            'headers': {
                'message-id': '20130503182626.18666.16540@sandboxf44696c342d9425abae785deb255717e.mailgun.org'
            }
        },
        'recipient': 'alice@example.com',
        'id': 'Ase7i2zsRYeDXztHGENqRA',
    },
}
mailgun_tracking_permanent_failure = {
    'signature': {
        'timestamp': '1608722011',
        'token': 'cd9604253476ab10e4bbbad7e07b74e417a364eed41d4c839d',
        'signature': _mailgun_signature(
            '1608722011', 'cd9604253476ab10e4bbbad7e07b74e417a364eed41d4c839d'
        ),
    },
    'event-data': {
        'severity': 'permanent',
        'tags': ['my_tag_1', 'my_tag_2'],
        'timestamp': 1521233195.375624,
        'storage': {
            'url': 'https://se.api.mailgun.net/v3/domains/sandboxf44696c342d9425abae785deb255717e.mailgun.org/messages/message_key',
            'key': 'message_key',
        },
        'log-level': 'error',
        'id': 'G9Bn5sl1TC6nu79C8C0bwg',
        'campaigns': [],
        'reason': 'suppress-bounce',
        'user-variables': {'my_var_1': 'Mailgun Variable #1', 'my-var-2': 'awesome'},
        'flags': {
            'is-routed': False,
            'is-authenticated': True,
            'is-system-test': False,
            'is-test-mode': False,
        },
        'recipient-domain': 'example.com',
        'envelope': {
            'sender': 'bob@sandboxf44696c342d9425abae785deb255717e.mailgun.org',
            'transport': 'smtp',
            'targets': 'alice@example.com',
        },
        'message': {
            'headers': {
                'to': 'Alice <alice@example.com>',
                'message-id': '20130503192659.13651.20287@sandboxf44696c342d9425abae785deb255717e.mailgun.org',
                'from': 'Bob <bob@sandboxf44696c342d9425abae785deb255717e.mailgun.org>',
                'subject': 'Test permanent_fail webhook',
            },
            'attachments': [],
            'size': 111,
        },
        'recipient': 'alice@example.com',
        'event': 'failed',
        'delivery-status': {
            'attempt-no': 1,
            'message': '',
            'code': 605,
            'description': 'Not delivering to previously bounced address',
            'session-seconds': 0,
        },
    },
}
mailgun_tracking_complained = {
    'signature': {
        'timestamp': '1608732345',
        'token': 'b009451600e91dbe015f81b415b74fa0b3a7d254d213cabe23',
        'signature': _mailgun_signature(
            '1608732345', 'b009451600e91dbe015f81b415b74fa0b3a7d254d213cabe23'
        ),
    },
    'event-data': {
        'tags': ['my_tag_1', 'my_tag_2'],
        'timestamp': 1521233123.501324,
        'envelope': {'sending-ip': '173.193.210.33'},
        'log-level': 'warn',
        'event': 'complained',
        'campaigns': [],
        'user-variables': {'my_var_1': 'Mailgun Variable #1', 'my-var-2': 'awesome'},
        'flags': {'is-test-mode': False},
        'message': {
            'headers': {
                'to': 'Alice <alice@example.com>',
                'message-id': '20110215055645.25246.63817@sandboxf44696c342d9425abae785deb255717e.mailgun.org',
                'from': 'Bob <bob@sandboxf44696c342d9425abae785deb255717e.mailgun.org>',
                'subject': 'Test complained webhook',
            },
            'attachments': [],
            'size': 111,
        },
        'recipient': 'alice@example.com',
        'id': '-Agny091SquKnsrW2NEKUA',
    },
}


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
@patch('storages.backends.s3boto3.S3Boto3Storage.url', Mock(return_value='s3://file'))
@patch(
    # Make sure background task is executed as a normal function
    'users.views.webhooks.handle_user_modified',
    new=webhooks.handle_user_modified.task_function,
)
class TestBlenderIDWebhook(TestCase):
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

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Invalid HMAC')

    def test_user_modified_invalid_hmac(self):
        url = reverse('webhook-user-modified')
        headers = {'HTTP_X-Webhook-HMAC': 'deadbeef'}
        response = self.client.post(url, {}, content_type='application/json', **headers)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Invalid HMAC')

    @patch('users.views.webhooks.WEBHOOK_MAX_BODY_SIZE', 1)
    def test_user_modified_request_body_too_large(self):
        body = {"deadbeef": "foobar"}
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 413)

    def test_user_modified_unexpected_content_type(self):
        response = self.client.post(
            self.url, 'text', content_type='text/plain', **prepare_hmac_header(b'text')
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Unsupported Content-Type')

    def test_user_modified_malformed_json(self):
        body = b'{"":"",}'
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Malformed JSON')

    @responses.activate
    def test_user_modified_updates_user(self):
        body = self.webhook_payload
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        user = User.objects.get(id=self.user.pk)
        self.assertEqual(user.full_name, 'Иван Васильевич Doe')
        self.assertEqual(user.email, 'newmail@example.com')
        self.assertEqual(
            user.badges,
            {
                'cloud_demo': {
                    'description': 'Blender Studio free account',
                    'image': 'http://id.local:8000/media/badges/badge_cloud.png',
                    'image_height': 256,
                    'image_width': 256,
                    'label': 'Blender Studio',
                }
            },
        )

    @responses.activate
    def test_user_modified_roles_added_removed_adds_removes_user_groups(self):
        # No groups ("roles") assigned yet
        self.assertEqual(list(self.user.groups.all()), [])

        # Two new roles added
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription', 'cloud_subscriber'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(
            sorted([g.name for g in user.groups.all()]),
            ['has_subscription', 'subscriber'],
        )

        # One role removed
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(
            sorted([g.name for g in user.groups.all()]),
            ['has_subscription'],
        )
        # Check that the group itself still exists
        self.assertEqual(Group.objects.filter(name='subscriber').count(), 1)

        # Two roles added, one already exists
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription', 'cloud_subscriber', 'dev_core'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(
            sorted([g.name for g in user.groups.all()]),
            ['dev_core', 'has_subscription', 'subscriber'],
        )

    @responses.activate
    def test_user_modified_roles_added_removed_adds_removes_user_groups_keeps_internal_groups(self):
        for group_name in ('_editor', '_org_someinc'):
            group, _ = Group.objects.get_or_create(name=group_name)
            self.user.groups.add(group)
        self.assertEqual(self.user.groups.count(), 2)

        # Two new roles added
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription', 'cloud_subscriber'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        user = User.objects.get(pk=self.user.pk)
        # Groups stating with an "_" are managed by Blender Studio, not Blender ID,
        # and should not be affected by the webhook
        self.assertEqual(
            sorted([g.name for g in user.groups.all()]),
            ['_editor', '_org_someinc', 'has_subscription', 'subscriber'],
        )

        # One role removed
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(
            sorted([g.name for g in user.groups.all()]),
            ['_editor', '_org_someinc', 'has_subscription'],
        )
        # Check that the group itself still exists
        self.assertEqual(Group.objects.filter(name='subscriber').count(), 1)

        # Two roles added, one already exists
        body = {
            **self.webhook_payload,
            'roles': ['cloud_has_subscription', 'cloud_subscriber', 'dev_core'],
        }
        response = self.client.post(
            self.url, body, content_type='application/json', **prepare_hmac_header(body)
        )

        self.assertEqual(response.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(
            sorted([g.name for g in user.groups.all()]),
            ['_editor', '_org_someinc', 'dev_core', 'has_subscription', 'subscriber'],
        )

    def test_user_modified_missing_oauth_info(self):
        body = {
            **self.webhook_payload,
            'id': '999',
        }
        with self.assertLogs('users.views.webhooks', level='WARNING') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(logs.output[0], 'Cannot update user: no OAuth info found for ID 999')

        self.assertEqual(response.status_code, 204)

    @responses.activate
    def test_user_modified_logs_errors_when_blender_id_user_info_broken(self):
        body = self.webhook_payload
        # Mock a "broken" user info response
        responses.replace(
            responses.GET, f'{BLENDER_ID_BASE_URL}api/me', status=403, body='Unauthorized'
        )

        with self.assertLogs('users.blender_id', level='WARNING') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(logs.output[0], 'Unable to update username for ')

        self.assertEqual(response.status_code, 204)

    @responses.activate
    def test_user_modified_avatar_changed(self):
        body = {
            **self.webhook_payload,
            'avatar_changed': True,
        }

        with self.assertLogs('users.blender_id', level='INFO') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(logs.output[0], 'Profile image updated for')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        user = User.objects.get(id=self.user.pk)
        self.assertTrue(user.image_url, 's3://file')

    @responses.activate
    def test_user_modified_date_deletion_requested_is_set(self):
        date_deletion_requested = '2020-12-31T23:02:03+00:00'
        body = {
            **self.webhook_payload,
            'date_deletion_requested': date_deletion_requested,
        }

        with self.assertLogs('users.models', level='WARNING') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertEqual(
                logs.output[0],
                f'WARNING:users.models:Deletion of pk={self.user.pk}'
                f' requested on {date_deletion_requested}, deactivating this account',
            )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        user = User.objects.get(id=self.user.pk)
        self.assertEqual(
            user.date_deletion_requested, dateutil.parser.parse(date_deletion_requested)
        )
        self.assertFalse(user.is_active)


@override_settings(
    BLENDER_ID={
        'BASE_URL': BLENDER_ID_BASE_URL,
        'OAUTH_CLIENT': 'testoauthclient',
        'OAUTH_SECRET': 'testoathsecret',
        'WEBHOOK_USER_MODIFIED_SECRET': b'testsecret',
    }
)
@patch('storages.backends.s3boto3.S3Boto3Storage.url', Mock(return_value='s3://file'))
@patch(
    # Make sure background task is executed as a normal function
    'users.views.webhooks.handle_user_modified',
    new=webhooks.handle_user_modified.task_function,
)
class TestIntegrityErrors(TransactionTestCase):
    """Check that webhook handles cases that trigger `IntegrityError`s.

    In order to do that, it has to handle database transactions commits and rollbacks the same way
    "normal" code does, as opposed to how TestCase does it, otherwise it breaks test runs.
    See https://docs.djangoproject.com/en/3.0/topics/testing/tools/#django.test.TransactionTestCase
    """

    maxDiff = None
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

    @responses.activate
    def test_user_modified_does_not_allow_duplicate_email(self):
        # Same email as in the webhook payload for another user
        another_user = UserFactory(email='jane@example.com')
        body = {
            **self.webhook_payload,
            'email': 'jane@example.com',
        }

        with self.assertLogs('users.views.webhooks', level='ERROR') as logs:
            response = self.client.post(
                self.url, body, content_type='application/json', **prepare_hmac_header(body)
            )
            self.assertRegex(logs.output[0], 'Unable to update email for')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        # Email was not updated
        self.assertEqual(self.user.email, 'mail@example.com')
        self.assertEqual(another_user.email, 'jane@example.com')


@override_settings(
    MAILGUN_API_KEY='test-api-key',
    ANYMAIL={
        'MAILGUN_API_KEY': 'test-api-key',
        'MAILGUN_SENDER_DOMAIN': 'sandboxtest.mailgun.org',
        'WEBHOOK_SECRET': None,
        'MAILGUN_WEBHOOK_SIGNING_KEY': 'test-signing-key',
    },
)
@patch(
    'users.tasks.handle_tracking_event_unsubscribe',
    new=tasks.handle_tracking_event_unsubscribe.task_function,
)
class TestMailgunWebhook(TestCase):
    maxDiff = None

    def setUp(self):
        # Make sure there's an admin account for use in LogEntry
        UserFactory(is_superuser=True)
        self.user = UserFactory(email='alice@example.com', is_subscribed_to_newsletter=True)
        self.url = '/webhooks/mailgun/tracking/'

    def test_unsubscribed_calls_task(self):
        self.assertTrue(self.user.is_subscribed_to_newsletter)

        response = self.client.post(
            self.url, data=mailgun_tracking_unsubscribed, content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscribed_to_newsletter)
        log_entry = LogEntry.objects.get(
            action_flag=CHANGE, object_id=self.user.pk, object_repr=str(self.user)
        )
        self.assertEqual(
            log_entry.change_message,
            'is_subscribed_to_newsletter changed. Reason: unsubscribed at Mailgun',
        )

    def test_permanent_failure_bounced_calls_task(self):
        self.assertTrue(self.user.is_subscribed_to_newsletter)

        response = self.client.post(
            self.url, data=mailgun_tracking_permanent_failure, content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscribed_to_newsletter)
        log_entry = LogEntry.objects.get(
            action_flag=CHANGE, object_id=self.user.pk, object_repr=str(self.user)
        )
        self.assertEqual(
            log_entry.change_message,
            'is_subscribed_to_newsletter changed due to permanently failed delivery at Mailgun. Reason: suppress-bounce, message: , list: ',
        )

    def test_complained_calls_task(self):
        self.assertTrue(self.user.is_subscribed_to_newsletter)

        response = self.client.post(
            self.url, data=mailgun_tracking_complained, content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscribed_to_newsletter)
        log_entry = LogEntry.objects.get(
            action_flag=CHANGE, object_id=self.user.pk, object_repr=str(self.user)
        )
        self.assertEqual(
            log_entry.change_message,
            'is_subscribed_to_newsletter changed. Reason: complained at Mailgun',
        )
