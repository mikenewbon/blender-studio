from datetime import timedelta
from unittest import mock
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.test import override_settings
from django.utils import timezone
import responses

from looper import admin_log
from looper.clock import Clock
from looper.models import Gateway, Subscription
from looper.money import Money

from common.tests.factories.subscriptions import (
    SubscriptionFactory,
    create_customer_with_billing_address,
)
from subscriptions.tests.base import BaseSubscriptionTestCase
import subscriptions.tasks
import users.tasks
import users.tests.util as util


class TestClock(BaseSubscriptionTestCase):
    def _create_subscription_due_now(self) -> Subscription:
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        now = timezone.now()
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = now + relativedelta(months=-1)
            # print('fake now:', mock_now.return_value)
            subscription = SubscriptionFactory(
                user=user,
                payment_method__user_id=user.pk,
                payment_method__recognisable_name='Test payment method',
                payment_method__gateway=Gateway.objects.get(name='braintree'),
                currency='USD',
                price=Money('USD', 1110),
                status='active',
            )
        # Sanity check: next payment should be due now:
        self.assertAlmostEqual(now, subscription.next_payment, delta=timedelta(hours=2))
        # Sanity check: no orders generated yet:
        self.assertIsNone(subscription.latest_order())
        return subscription

    def setUp(self):
        super().setUp()
        self.subscription = self._create_subscription_due_now()

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    def test_automated_payment_soft_failed_email_is_sent(self):
        now = timezone.now()

        # Tick the clock and check that order and transaction were created
        Clock().tick()

        # The subscription should not be renewed
        self.subscription.refresh_from_db()
        self.assertEqual('active', self.subscription.status)
        self.assertEqual(1, self.subscription.intervals_elapsed)
        self.assertAlmostEqual(now, self.subscription.next_payment, delta=timedelta(hours=2))

        # Test the order
        new_order = self.subscription.latest_order()
        self.assertEqual('soft-failed', new_order.status)
        self.assertEqual(1, new_order.collection_attempts)
        self.assertIsNotNone(new_order.number)
        self.assertAlmostEqual(now, new_order.retry_after, delta=timedelta(days=3))

        # Test the transaction
        new_transaction = new_order.latest_transaction()
        self.assertEqual('failed', new_transaction.status)
        self.assertEqual(
            'Cannot determine payment method: code 91508', new_transaction.failure_message
        )
        self.assertEqual(self.subscription.price, new_transaction.amount)
        entries_q = admin_log.entries_for(new_transaction)
        self.assertEqual(1, len(entries_q))
        self.assertIn('fail', entries_q.first().change_message)

        # Check that an email notification is sent
        self._assert_payment_soft_failed_email_is_sent(self.subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    @patch(
        'users.signals.tasks.revoke_blender_id_role',
        new=users.tasks.revoke_blender_id_role.task_function,
    )
    @responses.activate
    def test_automated_payment_failed_email_is_sent(self):
        now = timezone.now()
        order = self.subscription.generate_order()
        # Make the clock attempt to charge the same order one last time
        order.retry_after = now - timedelta(seconds=2)
        order.collection_attempts = 2
        order.status = 'soft-failed'
        order.save(update_fields={'collection_attempts', 'retry_after', 'status'})
        self.assertIsNotNone(self.subscription.latest_order())

        # Tick the clock and check that order and transaction were created
        util.mock_blender_id_badger_badger_response(
            'revoke', 'cloud_subscriber', self.subscription.user.oauth_info.oauth_user_id
        )
        Clock().tick()

        # The subscription should be on hold
        self.subscription.refresh_from_db()
        self.assertEqual('on-hold', self.subscription.status)
        self.assertEqual(0, self.subscription.intervals_elapsed)
        self.assertAlmostEqual(now, self.subscription.next_payment, delta=timedelta(hours=2))

        # Test the order
        new_order = self.subscription.latest_order()
        # It must be the same order
        self.assertEqual(order.pk, new_order.pk)
        self.assertEqual('failed', new_order.status)
        self.assertEqual(3, new_order.collection_attempts)
        self.assertAlmostEqual(now, new_order.retry_after, delta=timedelta(days=3))

        # Test the transaction
        new_transaction = new_order.latest_transaction()
        self.assertEqual('failed', new_transaction.status)
        self.assertEqual(
            'Cannot determine payment method: code 91508', new_transaction.failure_message
        )
        self.assertEqual(self.subscription.price, new_transaction.amount)
        entries_q = admin_log.entries_for(new_transaction)
        self.assertEqual(1, len(entries_q))
        self.assertIn('fail', entries_q.first().change_message)

        # Check that an email notification is sent
        self._assert_payment_failed_email_is_sent(self.subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    @patch('users.signals.tasks.revoke_blender_id_role')
    @responses.activate
    def test_automated_payment_failed_email_but_another_active_subscription_exists(
        self, mock_revoke_blender_id_role
    ):
        now = timezone.now()
        order = self.subscription.generate_order()
        # Make the clock attempt to charge the same order one last time
        order.retry_after = now - timedelta(seconds=2)
        order.collection_attempts = 2
        order.status = 'soft-failed'
        order.save(update_fields={'collection_attempts', 'retry_after', 'status'})
        self.assertIsNotNone(self.subscription.latest_order())

        # Create another active subscription for the same user
        SubscriptionFactory(
            user=self.subscription.user,
            payment_method=self.subscription.payment_method,
            currency='USD',
            price=Money('USD', 1110),
            status='active',
        )

        # Tick the clock and check that order and transaction were created
        Clock().tick()

        # Check that an email notification is sent
        self._assert_payment_failed_email_is_sent(self.subscription)

        # But badge has not be revoked
        mock_revoke_blender_id_role.assert_not_called()

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    def test_automated_payment_paid_email_is_sent(self):
        now = timezone.now()

        # Tick the clock and check that subscription renews, order and transaction were created
        with patch(
            'looper.gateways.BraintreeGateway.transact_sale', return_value='mock-transaction-id'
        ):
            Clock().tick()

        # Test the order
        new_order = self.subscription.latest_order()
        self.assertEqual('paid', new_order.status)
        self.assertEqual(1, new_order.collection_attempts)
        self.assertIsNone(new_order.retry_after)
        self.assertIsNotNone(new_order.number)
        # self.assertNotEqual(last_order_pk, new_order.pk)

        # The subscription should be renewed now.
        self.subscription.refresh_from_db()
        self.assertEqual('active', self.subscription.status)
        self.assertEqual(1, self.subscription.intervals_elapsed)
        self.assertAlmostEqual(
            now + relativedelta(months=1),
            self.subscription.next_payment,
            delta=timedelta(seconds=1),
        )

        # Test the transaction
        new_transaction = new_order.latest_transaction()
        self.assertEqual('succeeded', new_transaction.status)
        self.assertEqual(self.subscription.price, new_transaction.amount)
        entries_q = admin_log.entries_for(new_transaction)
        self.assertEqual(1, len(entries_q))
        self.assertIn('success', entries_q.first().change_message)

        # Check that an email notification is sent
        self._assert_payment_paid_email_is_sent(self.subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_managed_subscription_notification',
        new=subscriptions.tasks.send_mail_managed_subscription_notification.task_function,
    )
    @override_settings(LOOPER_MANAGER_MAIL='admin@example.com')
    def test_managed_subscription_notification_email_is_sent(self):
        now = timezone.now()
        self.subscription.collection_method = 'managed'
        self.subscription.save(update_fields={'collection_method'})

        # Tick the clock and check that subscription renews, order and transaction were created
        Clock().tick()

        # The subscription should be renewed now.
        self.subscription.refresh_from_db()
        self.assertEqual('active', self.subscription.status)
        self.assertEqual(1, self.subscription.intervals_elapsed)
        self.assertAlmostEqual(now, self.subscription.next_payment, delta=timedelta(seconds=1))
        self.assertAlmostEqual(now, self.subscription.last_notification, delta=timedelta(seconds=1))

        # Check that an email notification is sent
        self._assert_managed_subscription_notification_email_is_sent(self.subscription)


class TestClockExpiredSubscription(BaseSubscriptionTestCase):
    def test_subscription_on_hold_not_long_enough(self):
        now = timezone.now()
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.subscription = SubscriptionFactory(
            user=user,
            status='on-hold',
            # payment date has passed, but not long enough ago
            next_payment=now - timedelta(weeks=4),
        )

        Clock().tick()

        # Check that nothing has happened
        self.subscription.refresh_from_db()
        self.assertEqual('on-hold', self.subscription.status)
        self.assertFalse(self.subscription.is_cancelled)
        self.assertIsNone(self.subscription.cancelled_at)
        self._assert_no_emails_sent()

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_subscription_expired',
        new=subscriptions.tasks.send_mail_subscription_expired.task_function,
    )
    @patch(
        'users.signals.tasks.revoke_blender_id_role',
        new=users.tasks.revoke_blender_id_role.task_function,
    )
    @responses.activate
    def test_subscription_on_hold_too_long_status_changed_to_expired_email_sent(self):
        now = timezone.now()
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.subscription = SubscriptionFactory(
            user=user,
            status='on-hold',
            # payment date has passed a long long time ago
            next_payment=now - timedelta(weeks=4 * 10),
        )
        util.mock_blender_id_badger_badger_response(
            'revoke', 'cloud_subscriber', user.oauth_info.oauth_user_id
        )

        Clock().tick()

        # Check that subscription is expired now
        self.subscription.refresh_from_db()
        self.assertEqual('expired', self.subscription.status)
        self.assertTrue(self.subscription.is_cancelled)
        self.assertAlmostEqual(now, self.subscription.cancelled_at, delta=timedelta(seconds=1))

        # Check that an email notification is sent
        self._assert_subscription_expired_email_is_sent(self.subscription)
