from datetime import timedelta
import responses

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from comments.queries import set_comment_like
from common.tests.factories.comments import CommentFactory
from common.tests.factories.subscriptions import (
    PaymentMethodFactory,
    TransactionFactory,
    create_customer_with_billing_address,
)
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
        util.create_admin_log_user()

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
        user = create_customer_with_billing_address(
            email='mail1@example.com', date_deletion_requested=now - timedelta(days=30)
        )
        # this user made some comments
        user_comments = [CommentFactory(user=user) for _ in range(2)]
        # this user liked some comments as well
        for _ in range(3):
            set_comment_like(comment_pk=CommentFactory().pk, user_pk=user.pk, like=True)
        user_likes = list(user.like_set.all())
        user_actions = list(user.actor_actions.all())
        # which means that this user also has some activity
        self.assertEqual(user.actor_actions.count(), len(user_likes))
        # and other comment authors still have notifications about their likes
        for like in user_likes:
            self.assertEqual(like.comment.user.notifications.count(), 1)

        with self.assertLogs('users.models', level='WARNING') as log:
            tasks.handle_deletion_request.task_function(pk=user.pk)
            self.assertRegex(
                log.output[0],
                f'User pk={user.pk} requested deletion and has no orders: deleting the account',
            )

        # user got deleted
        with self.assertRaises(User.DoesNotExist):
            user.refresh_from_db()
        # user actions got deleted
        for action in user_actions:
            with self.assertRaises(action.__class__.DoesNotExist):
                action.refresh_from_db()
        # comments remained mostly intact
        for comment in user_comments:
            comment.refresh_from_db()
            self.assertIsNone(comment.user)
            self.assertEqual(comment.username, '<deleted>')
        # same with the likes
        for like in user_likes:
            like.refresh_from_db()
            self.assertIsNone(like.user)
            self.assertEqual(like.username, '<deleted>')
            # the notification, however, is also deleted
            self.assertEqual(like.comment.user.notifications.count(), 0)

    def test_handle_deletion_request_user_has_orders(self):
        now = timezone.now()
        user = create_customer_with_billing_address(
            email='mail1@example.com', date_deletion_requested=now - timedelta(days=30)
        )
        # this user has a subscription with an order and a transaction
        payment_method = PaymentMethodFactory(user=user)
        transaction = TransactionFactory(
            user=user,
            order__price=990,
            order__tax_country='NL',
            order__payment_method=payment_method,
            order__subscription__payment_method=payment_method,
            order__subscription__user=user,
            order__user=user,
            payment_method=payment_method,
        )
        # this user made some comments
        user_comments = [CommentFactory(user=user) for _ in range(2)]
        # this user liked some comments as well
        for _ in range(3):
            set_comment_like(comment_pk=CommentFactory().pk, user_pk=user.pk, like=True)
        user_likes = list(user.like_set.all())
        user_actions = list(user.actor_actions.all())
        # which means that this user also has some activity
        self.assertEqual(user.actor_actions.count(), len(user_likes))
        # and other comment authors still have notifications about their likes
        for like in user_likes:
            self.assertEqual(like.comment.user.notifications.count(), 1)

        with self.assertLogs('users.models', level='WARNING') as log:
            tasks.handle_deletion_request.task_function(pk=user.pk)
            self.assertRegex(log.output[1], f'Anonymized user pk={user.pk}', log.output)

        # subscription and order records remained
        transaction.refresh_from_db()
        transaction.order.refresh_from_db()
        transaction.order.subscription.refresh_from_db()
        self.assertEqual(transaction.order.price._cents, 990)
        self.assertEqual(transaction.order.tax_country, 'NL')

        # user wasn't deleted but anonymised
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.full_name, '')
        self.assertTrue(user.email.startswith('del'))
        self.assertTrue(user.email.endswith('@example.com'))
        with self.assertRaises(User.customer.RelatedObjectDoesNotExist):
            user.customer
        self.assertEqual(user.address_set.count(), 0)
        self.assertEqual(user.paymentmethod_set.first().recognisable_name, '')

        # user actions got deleted
        for action in user_actions:
            with self.assertRaises(action.__class__.DoesNotExist):
                action.refresh_from_db()

        # comments remained mostly intact
        for comment in user_comments:
            comment.refresh_from_db()
            self.assertIsNone(comment.user)
            self.assertEqual(comment.username, '<deleted>')
        # same with the likes
        for like in user_likes:
            like.refresh_from_db()
            self.assertIsNone(like.user)
            self.assertEqual(like.username, '<deleted>')
            # the notification, however, is also deleted
            self.assertEqual(like.comment.user.notifications.count(), 0)
