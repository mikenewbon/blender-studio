from freezegun import freeze_time
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls.base import reverse
import responses

from common.tests.factories.users import UserFactory
import profiles.tests.util as util


session_cookie_value_anon = 'eyJuZXh0X2FmdGVyX2xvZ2luIjoiLyJ9.X4CFJQ.5wFiwDul5Z3u2LECPfN8n4iwRWI'
session_cookie_value = '.eJyNj7FOAzEQRP_FNYXtXdu7-YOIDkgkqpO9u9Yhogvc5USB-HesFNSUI703mvl27WKL2jq96XSt-22ebtd3W9zB-XXGejp_fbxA1vMiM2-f-3F_fZTnp9PRPbh9u2v_Qae-2ja7w23dbaS7pBq6r2CKRIXIAhoTQrJcg0QrENDHAtlHYo1AzGq5RQ0Yhpkk55JiIezWyYB8NRTM3ljBd05Ja5chgVUo7AWi1EytFh-imTKPWbKt_e9vCSCsraFwjKmOlmScAQYNPFZ1bIgk2f38AlUFXOw.X4B_wQ.5EQ4gtZeRkKciEa2VdJZe3J2Mrk'  # noqa: E501


@override_settings(BLENDER_CLOUD_SECRET_KEY='supersecret', BLENDER_CLOUD_AUTH_ENABLED=True)
@freeze_time('2020-10-14 11:41:11')  # test cookies contain fixed expiration times
class TestSessionMiddleware(TestCase):
    maxDiff = None

    def setUp(self):
        util.mock_blender_id_responses()
        self.test_url = reverse('film-list')

    def test_middleware_anonymous_session(self):
        self.client.cookies.load(
            {settings.BLENDER_CLOUD_SESSION_COOKIE_NAME: session_cookie_value_anon}
        )

        response = self.client.get(self.test_url)

        self.assertEquals(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    @responses.activate
    def test_middleware_creates_and_signs_in_an_already_authenticated_user(self):
        self.assertFalse(User.objects.filter(email='jane@example.com').exists())
        self.client.cookies.load({settings.BLENDER_CLOUD_SESSION_COOKIE_NAME: session_cookie_value})

        response = self.client.get(self.test_url)

        self.assertEquals(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='jane@example.com').exists())
        user = User.objects.get(email='jane@example.com')
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEquals(int(self.client.session['_auth_user_id']), user.pk)
        self.assertEquals(
            {g.name for g in user.groups.all()},
            {'dev_core', 'has_subscription', 'subscriber'},
        )

    @responses.activate
    def test_middleware_signs_in_an_already_authenticated_already_existing_user(self):
        existing_user = UserFactory(email='somemail@example.com', oauth_info__oauth_user_id='2')
        self.client.cookies.load({settings.BLENDER_CLOUD_SESSION_COOKIE_NAME: session_cookie_value})

        response = self.client.get(self.test_url)

        self.assertEquals(response.status_code, 200)
        user = User.objects.get(pk=existing_user.pk)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEquals(int(self.client.session['_auth_user_id']), user.pk)
        self.assertEquals(
            {g.name for g in user.groups.all()},
            {'dev_core', 'has_subscription', 'subscriber'},
        )
