from django.contrib.auth import get_user_model
from django.core import mail
from django.db.models import signals
from django.test import TestCase
from django.urls import reverse
import factory
import responses

from common.tests.factories.subscriptions import create_customer_with_billing_address
from common.tests.factories.users import UserFactory

User = get_user_model()


def _write_mail(mail, index=0):
    email = mail.outbox[index]
    name = email.subject.replace(' ', '_')
    with open(f'/tmp/{name}.txt', 'w+') as f:
        f.write(str(email.body))
    for content, mimetype in email.alternatives:
        with open(f'/tmp/{name}.{mimetype.replace("/", ".")}', 'w+') as f:
            f.write(str(content))


class BaseSubscriptionTestCase(TestCase):
    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUp(self):
        # Allow requests to Braintree Sandbox
        responses.add_passthru('https://api.sandbox.braintreegateway.com:443/')

        # Create the admin user used for logging
        self.admin_user = UserFactory(
            id=1, email='admin@blender.studio', is_staff=True, is_superuser=True
        )
        # Reset ID sequence to avoid clashing with an already used ID 1
        UserFactory.reset_sequence(100, force=True)

        self.user = create_customer_with_billing_address(
            full_name='Алексей Н.',
            company='Testcompany B.V.',
            street_address='Billing street 1',
            extended_address='Floor 1',
            locality='Amsterdam',
            postal_code='1000AA',
            region='North Holland',
            country='NL',
            vat_number='NL-KVK-41202535',
            billing_email='billing@example.com',
        )
        self.customer = self.user.customer
        self.billing_address = self.customer.billing_address

    def _assert_required_billing_details_updated(self, user):
        customer = user.customer
        address = customer.billing_address
        self.assertEqual(address.full_name, 'New Full Name')
        self.assertEqual(address.street_address, 'MAIN ST 1')
        self.assertEqual(address.locality, 'Amsterdam')
        self.assertEqual(address.postal_code, '1000 AA')
        self.assertEqual(address.country, 'NL')

    def _assert_billing_details_form_displayed(self, response):
        self.assertNotContains(response, 'Sign in with Blender ID')
        self._assert_continue_to_payment_displayed(response)
        self.assertContains(response, 'id_street_address')
        self.assertContains(response, 'id_full_name')

    def _assert_payment_form_displayed(self, response):
        self.assertNotContains(response, 'Pricing has been updated')
        self.assertNotContains(response, 'Continue to Payment')
        self.assertContains(response, 'payment method')
        self.assertContains(response, 'Confirm and Pay')

    def _assert_pricing_has_been_updated(self, response):
        self.assertContains(response, 'Pricing has been updated')
        self._assert_billing_details_form_displayed(response)

    def _assert_plan_selector_displayed(self, response):
        self.assertContains(
            response,
            '<option selected value="1" title="This subscription is renewed automatically. You can stop or cancel a subscription any time.">Automatic renewal</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="2" title="This subscription is renewed manually. You can leave it on-hold, or renew it when convenient.">Manual renewal</option>',
            html=True,
        )

    def _assert_continue_to_billing_displayed(self, response):
        self.assertContains(response, 'Continue to Billing')

    def _assert_continue_to_payment_displayed(self, response):
        self.assertContains(response, 'Continue to Payment')

    def _assert_plan_selector_with_sign_in_cta_displayed(self, response):
        self._assert_plan_selector_displayed(response)

        self.assertContains(response, 'Sign in with Blender ID')
        self.assertNotContains(response, 'Continue to Payment')
        self.assertNotContains(response, 'id_street_address')
        self.assertNotContains(response, 'id_full_name')

    def _assert_default_variation_selected_no_tax_usd(self, response):
        self._assert_plan_selector_no_tax(response)
        self.assertContains(
            response,
            '<option selected data-renewal-period="1 month" data-currency-symbol="$" data-plan-id="1" data-price="11.50" value="1">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">$&nbsp;11.50</span>',
            html=True,
        )

    def _assert_default_variation_selected_tax_21_eur(self, response):
        self.assertContains(
            response,
            '<option selected data-renewal-period="1 month" data-currency-symbol="€" data-plan-id="1" data-price="9.90" data-price-tax="2.08" data-tax-rate="21" data-tax-display-name="VAT" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;9.90</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;2.08)</span>',
            html=True,
        )

    def _assert_default_variation_selected_tax_19_eur(self, response):
        self.assertContains(
            response,
            '<option selected data-renewal-period="1 month" data-currency-symbol="€" data-plan-id="1" data-price="9.90" data-price-tax="1.88" data-tax-rate="19" data-tax-display-name="VAT" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;9.90</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 19% VAT (€&nbsp;1.88)</span>',
            html=True,
        )

    def _assert_total_default_variation_selected_eur(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;9.90</span>', html=True)
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

    def _assert_total_default_variation_selected_tax_21_eur(self, response):
        self._assert_total_default_variation_selected_eur(response)
        self.assertContains(
            response, '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;2.08)</span>', html=True
        )
        self.assertContains(response, 'Automatic ')
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

    def _assert_total_default_variation_selected_tax_19_eur(self, response):
        self._assert_total_default_variation_selected_eur(response)
        self.assertContains(
            response, '<span class="x-price-tax">Inc. 19% VAT (€&nbsp;1.88)</span>', html=True
        )
        self.assertContains(response, 'Automatic ')
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

    def _assert_total_default_variation_selected_tax_19_eur_reverse_charged(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;8.02</span>', html=True)

    def _assert_total_default_variation_selected_tax_21_eur_reverse_charged(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;7.82</span>', html=True)

    def _assert_total_default_variation_selected_usd(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">$&nbsp;11.50</span>', html=True)
        self.assertContains(response, 'Automatic ')
        self.assertNotContains(response, 'Inc.')

    def _assert_plan_selector_no_tax(self, response):
        self.assertNotContains(response, 'Inc. ')
        self.assertContains(
            response,
            '<span class="x-price-tax"></span>',
            html=True,
        )

    def _assert_form_us_address_is_displayed(self, response):
        self.assertContains(
            response,
            '<option value="US" selected>United States of America</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="NY" selected>New York</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="text" name="postal_code" value="12001" maxlength="255" placeholder="ZIP/Postal code" class="form-control" required id="id_postal_code">',
            html=True,
        )

    def _assert_transactionless_done_page_displayed(self, response_redirect):
        # Catch unexpected form errors so that they are displayed
        # FIXME(anna): context is modified by the code that renders email, cannot access the form
        # self.assertEqual(
        #    response_redirect.context['form'].errors if response_redirect.context else {},
        #    {},
        # )
        self.assertEqual(response_redirect.status_code, 302)
        # Follow the redirect
        response = self.client.get(response_redirect['Location'])
        self.assertContains(response, '<h2 class="h3">Bank details:</h2>', html=True)
        self.assertContains(response, 'on hold')
        self.assertContains(response, 'NL22 INGB 0005296212')
        subscription = response.wsgi_request.user.subscription_set.first()
        self.assertContains(
            response, f'Blender Cloud order-{subscription.latest_order().display_number}'
        )

    def _assert_done_page_displayed(self, response_redirect):
        # Catch unexpected form errors so that they are displayed
        # FIXME(anna): context is modified by the code that renders email, cannot access the form
        # self.assertEqual(
        #    response_redirect.context['form'].errors if response_redirect.context else {},
        #    {},
        # )
        self.assertEqual(response_redirect.status_code, 302)
        # Follow the redirect
        response = self.client.get(response_redirect['Location'])
        self.assertContains(response, 'Welcome to Blender Cloud')
        self.assertNotContains(response, 'Bank details')

    def _assert_bank_transfer_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription Bank Payment')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(
                f'Blender Cloud order-{subscription.latest_order().number}',
                email_body,
            )
            self.assertIn('NL22 INGB 0005296212', email_body)
            self.assertIn('Dear Jane Doe,', email_body)
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Manual renewal subscription', email_body)
            self.assertIn('€\xa014.90 per month', email_body)
            self.assertIn('Inc. 21% VAT', email_body)
            self.assertIn('is currently on hold', email_body)

    def _assert_subscription_activated_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription Activated')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('activated', email_body)
            self.assertIn(f'Dear {user.customer.full_name},', email_body)
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Automatic renewal subscription', email_body)
            self.assertIn('Blender Cloud Team', email_body)

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
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Blender Cloud Team', email_body)

    def _assert_payment_soft_failed_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(
            email.subject, "Blender Cloud Subscription: payment failed (but we'll try again)"
        )
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(f'Dear {user.customer.full_name},', email_body)
            self.assertIn('Automatic payment', email_body)
            self.assertIn('failed', email_body)
            self.assertIn('try again', email_body)
            self.assertIn('1 of 3', email_body)
            self.assertIn(
                reverse(
                    'subscriptions:pay-existing-order',
                    kwargs={'order_id': subscription.latest_order().pk},
                ),
                email_body,
            )
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Blender Cloud Team', email_body)

    def _assert_payment_failed_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription: payment failed')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(f'Dear {user.customer.full_name},', email_body)
            self.assertIn('Automatic payment', email_body)
            self.assertIn('failed', email_body)
            self.assertIn('3 times', email_body)
            self.assertIn(
                reverse(
                    'subscriptions:pay-existing-order',
                    kwargs={'order_id': subscription.latest_order().pk},
                ),
                email_body,
            )
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Blender Cloud Team', email_body)

    def _assert_payment_paid_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription: payment received')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(f'Dear {user.customer.full_name},', email_body)
            self.assertIn('Automatic monthly payment', email_body)
            self.assertIn('successful', email_body)
            self.assertIn('$\xa011.10', email_body)
            self.assertIn(
                reverse(
                    'subscriptions:receipt', kwargs={'order_id': subscription.latest_order().pk}
                ),
                email_body,
            )
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Blender Cloud Team', email_body)

    def _assert_managed_subscription_notification_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['admin@example.com'])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud managed subscription needs attention')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(f'{user.customer.full_name} has', email_body)
            self.assertIn('its next payment date', email_body)
            self.assertIn('$\xa011.10', email_body)
            self.assertIn(
                f'/admin/looper/subscription/{subscription.pk}/change',
                email_body,
            )
