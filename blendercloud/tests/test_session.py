from unittest.mock import patch, ANY

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TransactionTestCase, TestCase, override_settings
import responses

import blender_id_oauth_client.models as models
from blendercloud.session import get_or_create_current_user, open_session
from common.tests.factories.users import UserFactory
import profiles.tests.util as util


session_cookie_value_anon = 'eyJuZXh0X2FmdGVyX2xvZ2luIjoiLyJ9.X4CFJQ.5wFiwDul5Z3u2LECPfN8n4iwRWI'
session_cookie_value = '.eJyNj7FOAzEQRP_FNYXtXdu7-YOIDkgkqpO9u9Yhogvc5USB-HesFNSUI703mvl27WKL2jq96XSt-22ebtd3W9zB-XXGejp_fbxA1vMiM2-f-3F_fZTnp9PRPbh9u2v_Qae-2ja7w23dbaS7pBq6r2CKRIXIAhoTQrJcg0QrENDHAtlHYo1AzGq5RQ0Yhpkk55JiIezWyYB8NRTM3ljBd05Ja5chgVUo7AWi1EytFh-imTKPWbKt_e9vCSCsraFwjKmOlmScAQYNPFZ1bIgk2f38AlUFXOw.X4B_wQ.5EQ4gtZeRkKciEa2VdJZe3J2Mrk'  # noqa: E501


@override_settings(
    BLENDER_CLOUD_SECRET_KEY='supersecret', BLENDER_CLOUD_AUTH_ENABLED=True,
)
class TestSession(TestCase):
    maxDiff = None

    def setUp(self):
        self.factory = RequestFactory()
        util.mock_blender_id_responses()

    def test_open_session_authenticated_user(self):
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value

        session = open_session(request)

        self.assertDictEqual(
            session,
            {
                '_fresh': True,
                '_id': ANY,
                'csrf_token': ANY,
                'user_id': ANY,
                # We are only interested in this field:
                'blender_id_oauth_token': '0rh4aUVwpT36dVnch9squIuYKcSRUI',
            },
        )

    def test_open_session_broken_session_cookie(self):
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = 'foobar'

        session = open_session(request)

        self.assertDictEqual(session, {})

    def test_open_session_anonymous_session(self):
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value_anon

        session = open_session(request)

        self.assertDictEqual(session, {'next_after_login': '/'})

    def test_get_or_create_current_user_anonymous_session(self):
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value_anon

        user = get_or_create_current_user(request)

        self.assertIsNone(user)

    @responses.activate
    def test_get_or_create_current_user_creates_new_user(self):
        self.assertFalse(User.objects.filter(email='jane@example.com').exists())
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value

        user = get_or_create_current_user(request)

        assert user is not None
        self.assertEquals(user.username, 'ⅉanedoe')
        self.assertEquals(user.email, 'jane@example.com')
        self.assertEquals(user.oauth_info.oauth_user_id, '2')
        self.assertEquals(user.profile.full_name, 'ⅉane ⅅoe')
        self.assertTrue(user.profile.avatar.name.endswith('.jpg'))
        self.assertEquals(
            sorted([g.name for g in user.groups.all()]),
            ['dev_core', 'has_subscription', 'subscriber',],
        )

    @responses.activate
    def test_get_or_create_current_user_existing_user(self):
        existing_user = UserFactory(email='somemail@example.com', oauth_info__oauth_user_id='2',)
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value

        user = get_or_create_current_user(request)

        assert user is not None
        self.assertEquals(user.pk, existing_user.pk)
        self.assertEquals(user.username, 'ⅉanedoe')
        self.assertEquals(user.email, 'jane@example.com')
        self.assertEquals(user.oauth_info.oauth_user_id, '2')

    @responses.activate
    def test_get_or_create_current_user_allows_duplicate_email(self):
        UserFactory(email='jane@example.com',)
        existing_user = UserFactory(email='somemail@example.com', oauth_info__oauth_user_id='2',)
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value

        user = get_or_create_current_user(request)

        assert user is not None
        self.assertEquals(user.oauth_info.oauth_user_id, '2')
        self.assertEquals(user.pk, existing_user.pk)
        self.assertEquals(user.email, 'jane@example.com')

    @responses.activate
    def test_get_or_create_current_user_race_condition_in_oauth_info_creation(self):
        existing_user = UserFactory(
            # Same email and OAuth ID as in Blender ID user info
            email='jane@example.com',
            oauth_info__oauth_user_id='2',
        )
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value

        # Sort of emulate the situation when OAuthUserInfo was created by another request:
        # even though user record matching User and OAuthUserInfo exist, throw DoesNotExist
        with patch(
            'blendercloud.session.models.OAuthUserInfo.objects.get',
            side_effect=models.OAuthUserInfo.DoesNotExist(),
        ):
            user = get_or_create_current_user(request)

        assert user is not None
        self.assertEquals(models.OAuthUserInfo.objects.filter(oauth_user_id='2').count(), 1)
        self.assertEquals(User.objects.filter(email='jane@example.com').count(), 1)
        self.assertEquals(user.oauth_info.oauth_user_id, '2')
        self.assertEquals(user.pk, existing_user.pk)
        self.assertEquals(user.username, 'ⅉanedoe')
        self.assertEquals(user.email, 'jane@example.com')


@override_settings(
    BLENDER_CLOUD_SECRET_KEY='supersecret', BLENDER_CLOUD_AUTH_ENABLED=True,
)
class TestIntegrityErrors(TransactionTestCase):
    """Check that get_or_create_current_user handles cases that trigger `IntegrityError`s.

    In order to do that, it has to handle database transactions commits and rollbacks the same way
    "normal" code does, as opposed to how TestCase does it, otherwise it breaks test runs.
    See https://docs.djangoproject.com/en/3.0/topics/testing/tools/#django.test.TransactionTestCase
    """

    maxDiff = None

    def setUp(self):
        self.factory = RequestFactory()
        util.mock_blender_id_responses()

    @responses.activate
    def test_get_or_create_current_user_handles_duplicate_username(self):
        UserFactory(username='ⅉanedoe',)
        existing_user = UserFactory(email='somemail@example.com', oauth_info__oauth_user_id='2',)
        request = self.factory.get('/')
        request.COOKIES[settings.BLENDER_CLOUD_SESSION_COOKIE_NAME] = session_cookie_value

        with self.assertLogs('blendercloud.session', level='ERROR') as logs:
            user = get_or_create_current_user(request)

        self.assertRegex(logs.output[0], r'Unable to update user pk=\d+: duplicate username')
        assert user is not None
        self.assertEquals(user.oauth_info.oauth_user_id, '2')
        self.assertEquals(user.pk, existing_user.pk)
        # The OAuth ID is correct, however username had not been updated to match Blender ID's
        self.assertNotEquals(user.username, 'ⅉanedoe')
        self.assertEquals(user.username, existing_user.username)