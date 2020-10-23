from django.contrib.auth.models import Group, AnonymousUser
from django.template import engines
from django.test import TestCase
from django.test.client import RequestFactory

from common.tests.factories.users import UserFactory
from common.templatetags.common_extras import has_group

template_engine = engines['django']


class CommonExtrasTest(TestCase):
    maxDiff = None

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        self.request.user = AnonymousUser()

    def test_has_group_unknown_group(self):
        user = UserFactory(email='mail@example.com')

        self.assertFalse(has_group(user, 'doesnotexist'))

    def test_has_group_in_group_subscriber_and_demo_are_equivalent(self):
        user = UserFactory(email='mail@example.com')
        group, _ = Group.objects.get_or_create(name='demo')
        user.groups.add(group)

        self.assertTrue(has_group(user, 'demo'))
        self.assertTrue(has_group(user, 'subscriber'))

    def test_has_group_in_group(self):
        user = UserFactory(email='mail@example.com')
        for group_name in ('subscriber', 'has_subscription'):
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        self.assertTrue(has_group(user, 'subscriber'))
        self.assertTrue(has_group(user, 'has_subscription'))

    def test_has_group_not_in_group(self):
        user = UserFactory(email='mail@example.com')
        group, _ = Group.objects.get_or_create(name='has_subscription')
        user.groups.add(group)

        self.assertTrue(has_group(user, 'has_subscription'))
        self.assertFalse(has_group(user, 'subscriber'))

    def test_template_with_has_group(self):
        user = UserFactory(email='mail@example.com')
        group, _ = Group.objects.get_or_create(name='has_subscription')
        user.groups.add(group)

        template_text = """
        {% load common_extras %}{% spaceless %}
        {% if user|has_group:"has_subscription" %}has subscription{% else %}{% endif %}
        {% if user|has_group:"subscriber" %}{% else %}subscription not active{% endif %}
        {% endspaceless %}
        """
        template = template_engine.from_string(template_text)
        content = template.render({'user': user})

        self.assertEqual(content.strip(), 'has subscription\n        subscription not active')

    def test_template_with_shortcodes_require_subscriber_shows_nothing_for_anon(self):
        template_text = """
        {% load common_extras %}{% spaceless %}
        {% with_shortcodes text %}{% endspaceless %}
        """
        template = template_engine.from_string(template_text)
        content = template.render(
            {'request': self.request, 'text': '{youtube youtubeID cap="subscriber"}'}
        )

        self.assertEqual(content.strip(), '')

    def test_template_with_shortcodes_require_subscriber_shows_nocap_for_anon(self):
        template_text = """
        {% load common_extras %}{% spaceless %}
        {% with_shortcodes text %}{% endspaceless %}
        """
        template = template_engine.from_string(template_text)
        content = template.render(
            {
                'request': self.request,
                'text': '{youtube youtubeID cap="subscriber" nocap="Please subscribe"}',
            }
        )

        self.assertEqual(content.strip(), '<p class="shortcode nogroup">Please subscribe</p>')

    def test_template_with_shortcodes_require_subscriber_shows_fallback_for_anon(self):
        template_text = """
        {% load common_extras %}{% spaceless %}
        {% with_shortcodes text %}{% endspaceless %}
        """
        template = template_engine.from_string(template_text)
        content = template.render(
            {
                'request': self.request,
                'text': '{youtube youtubeID cap="subscriber" nogroup="Please subscribe"}',
            }
        )

        self.assertEqual(content.strip(), '<p class="shortcode nogroup">Please subscribe</p>')

    def test_template_with_shortcodes_require_subscriber(self):
        user = UserFactory(email='mail@example.com')
        group, _ = Group.objects.get_or_create(name='subscriber')
        user.groups.add(group)

        template_text = """
        {% load common_extras %}{% spaceless %}
        {% with_shortcodes text %}{% endspaceless %}
        """
        template = template_engine.from_string(template_text)

        self.request.user = user
        content = template.render(
            {'request': self.request, 'text': '{youtube youtubeID cap="subscriber"}'}
        )

        self.assertEqual(
            '<div class="embed-responsive embed-responsive-16by9">'
            '<iframe class="shortcode youtube embed-responsive-item" width="560" height="315"'
            ' src="https://www.youtube.com/embed/youtubeID?rel=0" frameborder="0"'
            ' allow="autoplay; encrypted-media" allowfullscreen>'
            '</iframe></div>',
            content.strip(),
        )
