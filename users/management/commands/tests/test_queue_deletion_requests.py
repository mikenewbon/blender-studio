from datetime import timedelta
from io import StringIO
from unittest.mock import patch, call

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from common.tests.factories.users import UserFactory


class QueueDeletionRequestsCommandTest(TestCase):
    @patch('users.tasks.handle_deletion_request')
    def test_command_nothing_to_do(self, mock_handle_deletion_request):
        out = StringIO()
        call_command('queue_deletion_requests', stdout=out)

        self.assertEqual(out.getvalue(), '')
        mock_handle_deletion_request.assert_not_called()

    @patch('users.tasks.handle_deletion_request')
    def test_command(self, mock_handle_deletion_request):
        now = timezone.now()
        # create some users
        for _ in range(2):
            UserFactory()
        # create some users who requested deletion too recently
        for _ in range(3):
            UserFactory(date_deletion_requested=now - timedelta(days=7))
        # create some users who requested deletion long enough ago
        users_to_delete = [
            UserFactory(date_deletion_requested=now - timedelta(days=30)) for _ in range(4)
        ]
        # create some users who requested deletion and have already been processed
        for i in range(2):
            UserFactory(
                date_deletion_requested=now - timedelta(days=30),
                is_active=False,
            )

        with self.assertLogs(
            'users.management.commands.queue_deletion_requests', level='INFO'
        ) as logs:
            call_command('queue_deletion_requests')
            self.assertRegex(logs.output[0], 'Found 4 deletion requests that need handling')

        mock_handle_deletion_request.assert_called()
        self.assertEqual(mock_handle_deletion_request.call_count, 4)
        self.assertEqual(
            sorted(mock_handle_deletion_request.mock_calls),
            [call(user.pk) for user in users_to_delete],
        )
