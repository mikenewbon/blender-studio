from datetime import timedelta
from unittest import mock
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.test import override_settings
from django.utils import timezone

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


class TestClock(BaseSubscriptionTestCase):
    def _create_subscription_due_now(self) -> Subscription:
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        now = timezone.now()
        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = now - timedelta(days=31)
            # print('fake now:', mock_now.return_value)
            subscription = SubscriptionFactory(
                user=user,
                payment_method__user_id=user.pk,
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

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    def test_automated_payment_soft_failed_email_is_sent(self):
        now = timezone.now()
        subscription = self._create_subscription_due_now()

        # Tick the clock and check that order and transaction were created
        Clock().tick()

        # The subscription should not be renewed
        subscription.refresh_from_db()
        self.assertEqual('active', subscription.status)
        self.assertEqual(1, subscription.intervals_elapsed)
        self.assertAlmostEqual(now, subscription.next_payment, delta=timedelta(hours=2))

        # Test the order
        new_order = subscription.latest_order()
        self.assertEqual('soft-failed', new_order.status)
        self.assertEqual(1, new_order.collection_attempts)
        self.assertAlmostEqual(now, new_order.retry_after, delta=timedelta(days=3))

        # Test the transaction
        new_transaction = new_order.latest_transaction()
        self.assertEqual('failed', new_transaction.status)
        self.assertEqual(
            'Cannot determine payment method: code 91508', new_transaction.failure_message
        )
        self.assertEqual(subscription.price, new_transaction.amount)
        entries_q = admin_log.entries_for(new_transaction)
        self.assertEqual(1, len(entries_q))
        self.assertIn('fail', entries_q.first().change_message)

        # Check that an email notification is sent
        self._assert_payment_soft_failed_email_is_sent(subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    def test_automated_payment_failed_email_is_sent(self):
        now = timezone.now()
        subscription = self._create_subscription_due_now()
        order = subscription.generate_order()
        # Make the clock attempt to charge the same order one last time
        order.retry_after = now - timedelta(seconds=2)
        order.collection_attempts = 2
        order.status = 'soft-failed'
        order.save(update_fields={'collection_attempts', 'retry_after', 'status'})
        self.assertIsNotNone(subscription.latest_order())

        # Tick the clock and check that order and transaction were created
        Clock().tick()

        # The subscription should be on hold
        subscription.refresh_from_db()
        self.assertEqual('on-hold', subscription.status)
        self.assertEqual(0, subscription.intervals_elapsed)
        self.assertAlmostEqual(now, subscription.next_payment, delta=timedelta(hours=2))

        # Test the order
        new_order = subscription.latest_order()
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
        self.assertEqual(subscription.price, new_transaction.amount)
        entries_q = admin_log.entries_for(new_transaction)
        self.assertEqual(1, len(entries_q))
        self.assertIn('fail', entries_q.first().change_message)

        # Check that an email notification is sent
        self._assert_payment_failed_email_is_sent(subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_automatic_payment_performed',
        new=subscriptions.tasks.send_mail_automatic_payment_performed.task_function,
    )
    def test_automated_payment_paid_email_is_sent(self):
        now = timezone.now()
        subscription = self._create_subscription_due_now()

        # Tick the clock and check that subscription renews, order and transaction were created
        with patch(
            'looper.gateways.BraintreeGateway.transact_sale', return_value='mock-transaction-id'
        ):
            Clock().tick()

        # Test the order
        new_order = subscription.latest_order()
        self.assertEqual('paid', new_order.status)
        self.assertEqual(1, new_order.collection_attempts)
        self.assertIsNone(new_order.retry_after)
        # self.assertNotEqual(last_order_pk, new_order.pk)

        # The subscription should be renewed now.
        subscription.refresh_from_db()
        self.assertEqual('active', subscription.status)
        self.assertEqual(1, subscription.intervals_elapsed)
        self.assertAlmostEqual(
            now + relativedelta(months=1), subscription.next_payment, delta=timedelta(seconds=1)
        )

        # Test the transaction
        new_transaction = new_order.latest_transaction()
        self.assertEqual('succeeded', new_transaction.status)
        self.assertEqual(subscription.price, new_transaction.amount)
        entries_q = admin_log.entries_for(new_transaction)
        self.assertEqual(1, len(entries_q))
        self.assertIn('success', entries_q.first().change_message)

        # Check that an email notification is sent
        self._assert_payment_paid_email_is_sent(subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_managed_subscription_notification',
        new=subscriptions.tasks.send_mail_managed_subscription_notification.task_function,
    )
    @override_settings(LOOPER_MANAGER_MAIL='admin@example.com')
    def test_managed_subscription_notification_email_is_sent(self):
        now = timezone.now()
        subscription = self._create_subscription_due_now()
        subscription.collection_method = 'managed'
        subscription.save(update_fields={'collection_method'})

        # Tick the clock and check that subscription renews, order and transaction were created
        Clock().tick()

        # The subscription should be renewed now.
        subscription.refresh_from_db()
        self.assertEqual('active', subscription.status)
        self.assertEqual(1, subscription.intervals_elapsed)
        self.assertAlmostEqual(now, subscription.next_payment, delta=timedelta(seconds=1))
        self.assertAlmostEqual(now, subscription.last_notification, delta=timedelta(seconds=1))

        # Check that an email notification is sent
        self._assert_managed_subscription_notification_email_is_sent(subscription)
