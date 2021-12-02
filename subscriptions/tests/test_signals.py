from unittest.mock import patch, Mock, call
import datetime

from django.test import TestCase
import responses

from common.queries import has_active_subscription
from common.tests.factories.subscriptions import TeamFactory
from common.tests.factories.users import UserFactory


@patch('looper.admin_log.attach_log_entry', Mock(return_value=None))
class TestAddToTeams(TestCase):
    @classmethod
    @patch('looper.admin_log.attach_log_entry', Mock(return_value=None))
    def setUpTestData(cls) -> None:
        cls.team = TeamFactory(
            seats=4,
            emails=['test1@example.com', 'test2@example.com'],
            name='Team Awesome',
            subscription__status='active',
        )
        cls.team_unlimited = TeamFactory(
            seats=None,
            name='Team Unlimited',
            email_domain='my-awesome-blender-studio.org',
            subscription__status='active',
        )

    @responses.activate
    @patch('users.tasks.grant_blender_id_role')
    def test_added_to_team_if_email_matches_email_domain(self, mock_grant_blender_id_role):
        self.assertEqual(self.team_unlimited.users.count(), 0)

        user = UserFactory(email=f'jane@{self.team_unlimited.email_domain}')

        self.assertTrue(has_active_subscription(user))
        self.assertEqual(self.team_unlimited.users.count(), 1)
        mock_grant_blender_id_role.assert_called_once_with(
            # the call must be delayed because OAuthUserInfo might not exist at the moment
            # when a newly registered User is added to the team because its email matches.
            pk=user.pk,
            role='cloud_subscriber',
            schedule=datetime.timedelta(seconds=120),
        )

    @patch('users.tasks.grant_blender_id_role')
    def test_added_to_team_granted_subscriber_badge_if_email_is_on_team_emails(
        self, mock_grant_blender_id_role
    ):
        self.assertEqual(self.team.users.count(), 0)

        user = UserFactory(email=self.team.emails[0])

        self.assertTrue(has_active_subscription(user))
        self.assertEqual(self.team.users.count(), 1)
        mock_grant_blender_id_role.assert_called_once_with(
            # the call must be delayed because OAuthUserInfo might not exist at the moment
            # when a newly registered User is added to the team because its email matches.
            pk=user.pk,
            role='cloud_subscriber',
            schedule=datetime.timedelta(seconds=120),
        )

    @patch('users.tasks.grant_blender_id_role')
    def test_not_added_to_team_when_all_seats_taken(self, mock_grant_blender_id_role):
        self.assertEqual(self.team.users.count(), 0)
        # Leave only one seat
        self.team.seats = 2
        self.team.email_domain = 'my-great-domain.edu'
        self.team.save(update_fields={'seats', 'email_domain'})

        user01 = UserFactory(email=self.team.emails[0])
        user02 = UserFactory(email=f'bob@{self.team.email_domain}')
        with self.assertLogs('subscriptions.models', level='WARNING') as log:
            user03 = UserFactory(email=f'john@{self.team.email_domain}')
            self.assertRegex(
                log.output[0],
                f'Not adding user pk={user03.pk} to team pk={self.team.pk}: 2 out of 2 seats taken',
            )

        # First and secord users both should have been added to the team
        self.assertTrue(has_active_subscription(user01))
        self.assertTrue(has_active_subscription(user02))
        # Third user should not have been added to the team, even though their email matches
        self.assertFalse(has_active_subscription(user03))
        self.assertEqual(self.team.users.count(), 2)
        self.assertEqual(self.team.seats, 2)
        # Only first and second users got granted a subscriber badge
        self.assertEqual(len(mock_grant_blender_id_role.mock_calls), 2)
        self.assertEqual(
            mock_grant_blender_id_role.mock_calls,
            [
                call(
                    pk=user01.pk, role='cloud_subscriber', schedule=datetime.timedelta(seconds=120)
                ),
                call(
                    pk=user02.pk, role='cloud_subscriber', schedule=datetime.timedelta(seconds=120)
                ),
            ],
        )
