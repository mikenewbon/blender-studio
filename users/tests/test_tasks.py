import responses

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from common.tests.factories.users import UserFactory
import users.tasks as tasks
import users.tests.util as util

User = get_user_model()


@override_settings(
    MAILGUN_API_KEY='test-api-key',
    MAILGUN_SENDER_DOMAIN='sandboxtest.mailgun.org',
    ANYMAIL={
        'MAILGUN_API_KEY': 'test-api-key',
        'MAILGUN_SENDER_DOMAIN': 'sandboxtest.mailgun.org',
        'WEBHOOK_SECRET': None,
        'MAILGUN_WEBHOOK_SIGNING_KEY': 'test-signing-key',
    },
)
class TestTasks(TestCase):
    def setUp(self):
        util.mock_mailgun_responses()

    @responses.activate
    def test_handle_is_subscribed_to_newsletter_true_subscribes(self):
        user = UserFactory(email='mail2@example.com', is_subscribed_to_newsletter=True)

        tasks.handle_is_subscribed_to_newsletter.task_function(pk=user.pk)

    @responses.activate
    def test_handle_is_subscribed_to_newsletter_false_unsubscribes(self):
        user = UserFactory(email='mail1@example.com', is_subscribed_to_newsletter=False)

        tasks.handle_is_subscribed_to_newsletter.task_function(pk=user.pk)
