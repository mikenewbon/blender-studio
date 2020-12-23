from unittest.mock import patch

from django.test import TestCase

from common.tests.factories.users import UserFactory


class TestSignals(TestCase):
    def setUp(self):
        self.user = UserFactory(email='mail@example.com')

    @patch('users.tasks.handle_is_subscribed_to_newsletter')
    def test_is_subscribed_to_newsletter_changed_task_called(self, mock_task):
        self.user.is_subscribed_to_newsletter = True
        self.user.full_name = 'New Name'
        self.user.save(update_fields=['is_subscribed_to_newsletter', 'full_name'])

        mock_task.assert_called_once_with(pk=self.user.pk)

    @patch('users.tasks.handle_is_subscribed_to_newsletter')
    def test_is_subscribed_to_newsletter_not_changed_task_not_called(self, mock_task):
        self.user.is_subscribed_to_newsletter = self.user.is_subscribed_to_newsletter
        self.user.full_name = 'New Name'
        self.user.save(update_fields=['is_subscribed_to_newsletter', 'full_name'])

        mock_task.assert_not_called()
