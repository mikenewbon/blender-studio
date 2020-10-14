from unittest.mock import ANY

from django.contrib.auth.models import Group, AnonymousUser
from django.template import engines
from django.test import RequestFactory, TestCase

from common.tests.factories.users import UserFactory
from profiles.context_processors import user_dict

template_engine = engines['django']


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
                'profile': None,
                'username': None,
            }
        )

    def test_user_dict_authenticated_user(self):
        user = UserFactory(
            email='mail@example.com',
            username='ⅉanedoe',
        )
        user.profile.full_name = 'ⅉane Doe'
        user.profile.avatar.name = 'cache/path/to/avatar.jpg'
        for group_name in ('has_subscription', 'subscriber'):
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
                'groups': [
                    {'name': 'has_subscription'},
                    {'name': 'subscriber'},
                ],
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'profile': {
                    'avatar_url': ANY,
                    'full_name': 'ⅉane Doe',
                },
                'username': 'ⅉanedoe',
            }
        )

    def test_user_dict_authenticated_user_no_avatar(self):
        user = UserFactory(
            email='mail@example.com',
            username='ⅉanedoe',
        )
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
                'profile': {
                    'avatar_url': None,
                    'full_name': '',
                },
                'username': 'ⅉanedoe',
            }
        )
