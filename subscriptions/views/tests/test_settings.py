from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from waffle.testutils import override_flag

from looper.models import PaymentMethod, PaymentMethodAuthentication, Gateway

from common.tests.factories.users import UserFactory
from common.tests.factories.subscriptions import SubscriptionFactory
from subscriptions.tests.base import _CreateCustomerAndBillingAddressMixin, _write_mail
import subscriptions.tasks

required_address_data = {
    'country': 'NL',
    'email': 'my.billing.email@example.com',
    'full_name': 'New Full Name',
    'locality': 'Amsterdam',
    'postal_code': '1000 AA',
    'street_address': 'MAIN ST 1',
}
full_billing_address_data = {
    **required_address_data,
    'extended_address': 'Floor 2',
    'company': 'Test LLC',
    'vat_number': 'NL818152011B01',
}


@override_flag('SUBSCRIPTIONS_ENABLED', active=True)
class TestSubscriptionSettingsBillingAddress(_CreateCustomerAndBillingAddressMixin, TestCase):
    def test_saves_both_address_and_customer(self):
        user = UserFactory()
        self.client.force_login(user)

        url = reverse('subscriptions:billing-address')
        response = self.client.post(url, full_billing_address_data)

        # Check that the redirect on success happened
        self.assertEqual(response.status_code, 302, response.content)
        self.assertEqual(response['Location'], url)

        # Check that all address fields were updated
        customer = user.customer
        address = customer.billing_address
        self.assertEqual(address.full_name, 'New Full Name')
        self.assertEqual(address.street_address, 'MAIN ST 1')
        self.assertEqual(address.extended_address, 'Floor 2')
        self.assertEqual(address.locality, 'Amsterdam')
        self.assertEqual(address.postal_code, '1000 AA')
        # self.assertEqual(address.region, 'North Holland')
        self.assertEqual(address.country, 'NL')
        self.assertEqual(address.company, 'Test LLC')

        # Check that customer fields were updated as well
        self.assertEqual(customer.vat_number, 'NL818152011B01')
        # N.B.: email is saved as Customer.billing_email
        self.assertEqual(customer.billing_email, 'my.billing.email@example.com')

    def test_invalid_missing_required_fields(self):
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.post(reverse('subscriptions:billing-address'), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'errorlist')
        self.assertContains(response, 'is required')

    def test_invalid_missing_required_full_name(self):
        user = UserFactory()
        self.client.force_login(user)

        data = {
            'email': 'new@example.com',
        }
        response = self.client.post(reverse('subscriptions:billing-address'), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'errorlist')
        self.assertContains(response, 'is required')

    def test_invalid_missing_required_email(self):
        user = UserFactory()
        self.client.force_login(user)

        data = {
            'full_name': 'New Full Name',
        }
        response = self.client.post(reverse('subscriptions:billing-address'), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'errorlist')
        self.assertContains(response, 'is required')


@override_flag('SUBSCRIPTIONS_ENABLED', active=True)
class TestSubscriptionSettingsChangePaymentMethod(_CreateCustomerAndBillingAddressMixin, TestCase):
    shared_payment_form_data = {
        **required_address_data,
        'next_url_after_done': '/settings/billing',
    }
    url_name = 'subscriptions:payment-method-change'
    success_url_name = 'user-settings-billing'

    def test_can_change_payment_method_from_bank_to_credit_card_with_sca(self):
        bank = Gateway.objects.get(name='bank')
        subscription = SubscriptionFactory(
            user=self.user,
            payment_method__user_id=self.user.pk,
            payment_method__gateway=bank,
        )
        self.assertEqual(PaymentMethod.objects.count(), 1)
        self.assertIsNone(PaymentMethodAuthentication.objects.first())
        payment_method = subscription.payment_method
        self.client.force_login(self.user)

        url = reverse(self.url_name, kwargs={'subscription_id': subscription.pk})
        data = {
            **self.shared_payment_form_data,
            'gateway': 'braintree',
            'payment_method_nonce': 'fake-three-d-secure-visa-full-authentication-nonce',
        }
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse(self.success_url_name))
        # New payment method was created
        self.assertEqual(PaymentMethod.objects.count(), 2)

        subscription.refresh_from_db()
        subscription.payment_method.refresh_from_db()
        # Subscription's payment method was changed to a credit card
        self.assertNotEqual(subscription.payment_method_id, payment_method.pk)
        self.assertEqual(
            str(subscription.payment_method),
            'braintree – Visa credit card ending in 0002',
        )
        # SCA was stored
        self.assertIsNotNone(PaymentMethodAuthentication.objects.first())

    def test_can_change_payment_method_from_credit_card_to_bank(self):
        braintree = Gateway.objects.get(name='braintree')
        subscription = SubscriptionFactory(
            user=self.user,
            payment_method__user_id=self.user.pk,
            payment_method__gateway=braintree,
        )
        self.assertEqual(PaymentMethod.objects.count(), 1)
        payment_method = subscription.payment_method
        self.client.force_login(self.user)

        url = reverse(self.url_name, kwargs={'subscription_id': subscription.pk})
        data = {
            **self.shared_payment_form_data,
            'gateway': 'bank',
            'payment_method_nonce': 'unused',
        }
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse(self.success_url_name))
        # New payment method was created
        self.assertEqual(PaymentMethod.objects.count(), 2)

        subscription.refresh_from_db()
        subscription.payment_method.refresh_from_db()
        # Subscription's payment method was changed to bank transfer
        self.assertNotEqual(subscription.payment_method_id, payment_method.pk)
        self.assertEqual(str(subscription.payment_method), 'bank – Bank Transfer')
        self.assertIsNone(PaymentMethodAuthentication.objects.first())


@override_flag('SUBSCRIPTIONS_ENABLED', active=True)
class TestSubscriptionCancel(_CreateCustomerAndBillingAddressMixin, TestCase):
    url_name = 'subscriptions:cancel'

    def _assert_subscription_deactivated_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription Deactivated')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('deactivated', email_body)
            self.assertIn('Dear Алексей Н.,', email_body)
            self.assertIn('/settings/billing', email_body)
            self.assertIn('Blender Cloud Team', email_body)

    def test_can_cancel_when_on_hold(self):
        subscription = SubscriptionFactory(
            user=self.user,
            payment_method__user_id=self.user.pk,
            payment_method__gateway=Gateway.objects.get(name='bank'),
            status='on-hold',
        )
        self.client.force_login(self.user)

        url = reverse(self.url_name, kwargs={'subscription_id': subscription.pk})
        data = {'confirm': True}
        with patch(
            # Make sure background task is executed as a normal function
            'subscriptions.signals.tasks.send_mail_subscription_status_changed',
            new=subscriptions.tasks.send_mail_subscription_status_changed.task_function,
        ):
            response = self.client.post(url, data=data)
        with open('/tmp/response.html', 'wb+') as f:
            f.write(response.content)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/settings/billing')

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'cancelled')
        # No email is sent when: pending-cancellation still means subscription is active

    def test_can_cancel_when_active(self):
        subscription = SubscriptionFactory(
            user=self.user,
            payment_method__user_id=self.user.pk,
            payment_method__gateway=Gateway.objects.get(name='bank'),
            status='active',
        )
        self.client.force_login(self.user)

        url = reverse(self.url_name, kwargs={'subscription_id': subscription.pk})
        data = {'confirm': True}
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/settings/billing')

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'pending-cancellation')
        # No email is sent when: pending-cancellation still means subscription is active

    def test_email_sent_when_pending_cancellation_changes_to_cancelled(self):
        subscription = SubscriptionFactory(
            user=self.user,
            payment_method__user_id=self.user.pk,
            payment_method__gateway=Gateway.objects.get(name='bank'),
            status='pending-cancellation',
        )

        with patch(
            # Make sure background task is executed as a normal function
            'subscriptions.signals.tasks.send_mail_subscription_status_changed',
            new=subscriptions.tasks.send_mail_subscription_status_changed.task_function,
        ):
            subscription.status = 'cancelled'
            subscription.save()

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, 'cancelled')

        self._assert_subscription_deactivated_email_is_sent(subscription)
