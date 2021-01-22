from datetime import timedelta
import responses

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from comments.queries import set_comment_like
from common.tests.factories.comments import CommentFactory
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

    def test_handle_deletion_request(self):
        now = timezone.now()
        user = UserFactory(
            email='mail1@example.com', date_deletion_requested=now - timedelta(days=30)
        )
        # this user made some comments
        user_comments = [CommentFactory(user=user) for _ in range(2)]
        # this user liked some comments as well
        for _ in range(3):
            set_comment_like(comment_pk=CommentFactory().pk, user_pk=user.pk, like=True)
        user_likes = user.like_set.all()
        # which means that this user also has some activity
        self.assertEquals(user.actor_actions.count(), len(user_likes))
        # and other comment authors still have notifications about their likes
        for like in user_likes:
            self.assertEquals(like.comment.user.notifications.count(), 1)

        with self.assertLogs('users.tasks', level='WARNING') as log:
            tasks.handle_deletion_request.task_function(pk=user.pk)
            self.assertRegex(log.output[0], f'Deleted user pk={user.pk}')

        # user got deleted
        with self.assertRaises(User.DoesNotExist):
            user.refresh_from_db()
        # comments remained mostly intact
        for comment in user_comments:
            comment.refresh_from_db()
            self.assertIsNone(comment.user)
            self.assertEquals(comment.username, '<deleted>')
        # same with the likes
        for like in user_likes:
            like.refresh_from_db()
            self.assertIsNone(like.user)
            self.assertEquals(like.username, '<deleted>')
            # the notification, however, is also deleted
            self.assertEquals(like.comment.user.notifications.count(), 0)
