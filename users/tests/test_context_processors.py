from unittest.mock import ANY, patch, Mock

from django.contrib.auth.models import Group, AnonymousUser
from django.template import engines
from django.test import RequestFactory, TestCase

from common.tests.factories.users import UserFactory
from users.context_processors import user_dict

template_engine = engines['django']


@patch('storages.backends.s3boto3.S3Boto3Storage.url', Mock(return_value='s3://file'))
class ContextProcessorsTest(TestCase):
    maxDiff = None

    def setUp(self):
        self.request = RequestFactory().get('/')
        self.request.user = AnonymousUser()

    def test_user_dict_anonymous_user(self):
        context = user_dict(self.request)

        self.assertDictEqual(
            context['user_dict'],
            {
                'is_anonymous': True,
                'is_authenticated': False,
                'date_joined': None,
                'groups': None,
                'is_active': None,
                'is_staff': None,
                'is_superuser': None,
                'last_login': None,
                'image_url': None,
                'full_name': None,
                'username': None,
                'badges': None,
            },
        )

    def test_user_dict_authenticated_user_with_oauth_info(self):
        user = UserFactory(
            email='mail@example.com',
            username='ⅉanedoe',
            oauth_info__oauth_user_id='2',
            badges={
                'cloud_demo': {
                    'label': 'Blender Studio',
                    'description': 'Blender Studio free account',
                    'image': 'http://id.local:8000/media/badges/badge_cloud.png',
                    'image_width': 256,
                    'image_height': 256,
                },
            },
        )
        user.full_name = 'ⅉane Doe'
        user.image = 'path/to/file'
        for group_name in ('subscriber', 'has_subscription'):
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        self.request.user = user

        context = user_dict(self.request)

        self.assertDictEqual(
            context['user_dict'],
            {
                'is_anonymous': False,
                'is_authenticated': True,
                'date_joined': ANY,
                'last_login': ANY,
                'groups': [{'name': 'subscriber'}, {'name': 'has_subscription'}],
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'image_url': 's3://file',
                'full_name': 'ⅉane Doe',
                'username': 'ⅉanedoe',
                'badges': {
                    'cloud_demo': {
                        'label': 'Blender Studio',
                        'description': 'Blender Studio free account',
                        'image': 'http://id.local:8000/media/badges/badge_cloud.png',
                        'image_width': 256,
                        'image_height': 256,
                    },
                },
            },
        )

    def test_user_dict_authenticated_user_without_oauth_info(self):
        user = UserFactory(email='mail@example.com', username='ⅉanedoe', oauth_info=None)
        self.request.user = user

        context = user_dict(self.request)

        self.assertDictEqual(
            context['user_dict'],
            {
                'is_anonymous': False,
                'is_authenticated': True,
                'date_joined': ANY,
                'last_login': None,
                'groups': [],
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'image_url': '/static/common/images/blank-profile-pic.png',
                'full_name': '',
                'username': 'ⅉanedoe',
                'badges': None,
            },
        )
