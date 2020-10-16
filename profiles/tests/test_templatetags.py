from django.contrib.auth.models import Group
from django.template import engines
from django.test import TestCase

from common.tests.factories.users import UserFactory
from profiles.templatetags.profile_extras import has_group

template_engine = engines['django']


class ProfileExtrasTest(TestCase):
    def test_has_group_unknown_group(self):
        user = UserFactory(email='mail@example.com',)

        self.assertFalse(has_group(user, 'doesnotexist'))

    def test_has_group_in_group(self):
        user = UserFactory(email='mail@example.com',)
        for group_name in ('subscriber', 'has_subscription'):
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        self.assertTrue(has_group(user, 'subscriber'))
        self.assertTrue(has_group(user, 'has_subscription'))

    def test_has_group_not_in_group(self):
        user = UserFactory(email='mail@example.com',)
        group, _ = Group.objects.get_or_create(name='has_subscription')
        user.groups.add(group)

        self.assertTrue(has_group(user, 'has_subscription'))
        self.assertFalse(has_group(user, 'subscriber'))

    def test_template_with_has_group(self):
        user = UserFactory(email='mail@example.com',)
        group, _ = Group.objects.get_or_create(name='has_subscription')
        user.groups.add(group)

        template_text = """
        {% load profile_extras %}{% spaceless %}
        {% if user|has_group:"has_subscription" %}has subscription{% else %}{% endif %}
        {% if user|has_group:"subscriber" %}{% else %}subscription not active{% endif %}
        {% endspaceless %}
        """
        template = template_engine.from_string(template_text)
        content = template.render({'user': user})

        self.assertEqual(content.strip(), 'has subscription\n        subscription not active')
