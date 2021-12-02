import os

from django.contrib.auth import get_user_model
from django.core import mail
from django.db.models import signals
from django.test import TestCase
from django.urls import reverse
import factory
import responses

from common.tests.factories.subscriptions import create_customer_with_billing_address
import users.tests.util as util

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
        self.admin_user = util.create_admin_log_user()

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

    def _mock_vies_response(self, is_valid=True, is_broken=False):
        path = os.path.abspath(__file__)
        dir_path = os.path.join(os.path.dirname(path), 'vies')

        vies_base_url = 'https://ec.europa.eu/taxation_customs/vies'
        wsdl_file = 'checkVatService.wsdl'
        with open(os.path.join(dir_path, wsdl_file), 'r') as f:
            responses.add(
                responses.GET,
                url=f'{vies_base_url}/checkVatService.wsdl',
                body=f.read(),
                content_type='text/xml',
            )

        post_xml_file = f'checkVatService_POST_{"valid" if is_valid else "invalid"}.xml'
        with open(os.path.join(dir_path, post_xml_file), 'r') as f:
            responses.add(
                responses.POST,
                url=f'{vies_base_url}/services/checkVatService',
                body=f.read(),
                content_type='text/xml',
                status=500 if is_broken else 200,
            )

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
        self.assertContains(response, 'Step 1: Choose your plan.', html=True)
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

    def _assert_team_plan_selector_displayed(self, response):
        self.assertContains(response, 'Step 1: Choose your team plan.', html=True)
        self.assertContains(
            response,
            '<option selected value="3" title="This subscription is renewed automatically. You can stop or cancel a subscription any time.">Automatic renewal, 15 seats</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="4" title="This subscription is renewed manually. You can leave it on-hold, or renew it when convenient.">Manual renewal, 15 seats</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="5" title="This subscription is renewed automatically. You can stop or cancel a subscription any time.">Automatic renewal, unlimited seats</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option value="6" title="This subscription is renewed manually. You can leave it on-hold, or renew it when convenient.">Manual renewal, unlimited seats</option>',
            html=True,
        )
        self.assertContains(response, '<span class="x-team-seats font-bold">15</span>', html=True)

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

    def _assert_team_plan_selector_with_sign_in_cta_displayed(self, response):
        self._assert_team_plan_selector_displayed(response)

        self.assertContains(response, 'Sign in with Blender ID')
        self.assertNotContains(response, 'Continue to Payment')
        self.assertNotContains(response, 'id_street_address')
        self.assertNotContains(response, 'id_full_name')

    def _assert_default_variation_selected_no_tax_usd(self, response):
        self._assert_plan_selector_no_tax(response)
        self.assertContains(
            response,
            '<option selected data-renewal-period="1 month" data-currency-symbol="$" data-plan-id="1" data-price="11.50" data-next-url="/join/plan-variation/1/" value="1">Every 1 month</option>',
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
            '<option selected data-renewal-period="1 month" data-currency-symbol="€" data-plan-id="1" data-price="9.90" data-price-tax="1.72" data-tax-rate="21" data-tax-display-name="VAT" data-next-url="/join/plan-variation/2/" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;9.90</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;1.72)</span>',
            html=True,
        )

    def _assert_default_team_variation_selected_tax_21_eur(self, response):
        self.assertContains(
            response,
            '<option selected data-team-seats="15" data-renewal-period="1 month" data-currency-symbol="€" data-plan-id="3" data-price="90.00" data-price-tax="15.62" data-tax-rate="21" data-tax-display-name="VAT" data-next-url="/join/team/plan-variation/16/" value="16">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;90.00</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;15.62)</span>',
            html=True,
        )

    def _assert_default_variation_selected_tax_20_eur(self, response):
        self.assertContains(
            response,
            '<option selected data-renewal-period="1 month" data-currency-symbol="€" data-plan-id="1" data-price="9.90" data-price-tax="1.65" data-tax-rate="20" data-tax-display-name="VAT" data-next-url="/join/plan-variation/2/" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;9.90</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 20% VAT (€&nbsp;1.65)</span>',
            html=True,
        )

    def _assert_default_variation_selected_tax_19_eur(self, response):
        self.assertContains(
            response,
            '<option selected data-renewal-period="1 month" data-currency-symbol="€" data-plan-id="1" data-price="9.90" data-price-tax="1.58" data-tax-rate="19" data-tax-display-name="VAT" data-next-url="/join/plan-variation/2/" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;9.90</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 19% VAT (€&nbsp;1.58)</span>',
            html=True,
        )

    def _assert_total_default_variation_selected_eur(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;9.90</span>', html=True)
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

    def _assert_total_default_variation_selected_no_tax_eur(self, response):
        self._assert_total_default_variation_selected_eur(response)
        self.assertContains(response, 'Automatic ')
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;9.90</span>', html=True)
        self.assertNotContains(response, 'Inc.')

    def _assert_total_default_variation_selected_tax_21_eur(self, response):
        self._assert_total_default_variation_selected_eur(response)
        self.assertContains(
            response, '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;1.72)</span>', html=True
        )
        self.assertContains(response, 'Automatic ')
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

    def _assert_total_default_variation_selected_tax_19_eur(self, response):
        self._assert_total_default_variation_selected_eur(response)
        self.assertContains(
            response, '<span class="x-price-tax">Inc. 19% VAT (€&nbsp;1.58)</span>', html=True
        )
        self.assertContains(response, 'Automatic ')
        self.assertContains(response, '/ <span class="x-price-period">1 month</span>', html=True)

    def _assert_total_default_variation_selected_tax_19_eur_reverse_charged(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;8.32</span>', html=True)

    def _assert_total_default_variation_selected_tax_21_eur_reverse_charged(self, response):
        self.assertContains(response, '<h3 class="mb-0">Total</h3>', html=True)
        self.assertContains(response, '<span class="x-price">€&nbsp;8.18</span>', html=True)

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
            '<input type="text" name="postal_code" value="12001" maxlength="255" placeholder="ZIP/Postal code" class="form-control" id="id_postal_code">',
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
        self.assertContains(response, 'NL07 INGB 0008 4489 82')
        subscription = response.wsgi_request.user.subscription_set.first()
        self.assertContains(
            response, f'Blender Studio order-{subscription.latest_order().display_number}'
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
        self.assertContains(response, 'Welcome to Blender Studio')
        self.assertNotContains(response, 'Bank details')

    def _assert_no_emails_sent(self):
        self.assertEqual(len(mail.outbox), 0)

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
        self.assertEqual(email.subject, 'Blender Studio Subscription Bank Payment')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(
                f'Blender Studio order-{subscription.latest_order().number}',
                email_body,
            )
            self.assertIn('NL07 INGB 0008 4489 82', email_body)
            self.assertIn('Dear Jane Doe,', email_body)
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Manual renewal subscription', email_body)
            self.assertIn('is currently on hold', email_body)

    def _assert_bank_transfer_email_is_sent_tax_21(self, subscription):
        email = mail.outbox[0]
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('€\xa014.90 per month', email_body)
            self.assertIn('Inc. 21% VAT', email_body)
            self.assertIn('Please send your payment of €\xa014.90 to', email_body)
            self.assertIn('Recurring total: €\xa014.90', email_body.replace('    ', ' '))

    def _assert_bank_transfer_email_is_sent_tax_21_eur_reverse_charged(self, subscription):
        email = mail.outbox[0]
        for email_body in (email.body, email.alternatives[0][0]):
            # "Original" subscription price must not be displayed anywhere, only the tax-exc one
            self.assertNotIn('32.00', email_body)
            self.assertNotIn('21%', email_body)
            self.assertNotIn('Inc.', email_body)
            self.assertNotIn('VAT', email_body)
            self.assertIn('€\xa026.45 per 3 months', email_body)
            self.assertIn('Please send your payment of €\xa026.45 to', email_body)
            self.assertIn('Recurring total: €\xa026.45', email_body.replace('    ', ' '))

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
        self.assertEqual(email.subject, 'Blender Studio Subscription Activated')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('activated', email_body)
            self.assertIn(f'Dear {user.customer.full_name},', email_body)
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Automatic renewal subscription', email_body)
            self.assertIn('Blender Studio Team', email_body)

    def _assert_team_subscription_activated_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.customer.billing_email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Studio Subscription Activated')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('activated', email_body)
            self.assertIn(f'Dear {user.customer.full_name},', email_body)
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Automatic renewal, 15 seats subscription', email_body)
            self.assertIn('Blender Studio Team', email_body)

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
        self.assertEqual(email.subject, 'Blender Studio Subscription Deactivated')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('deactivated', email_body)
            self.assertIn('Dear Алексей Н.,', email_body)
            self.assertIn(reverse('user-settings-billing'), email_body)
            self.assertIn('Blender Studio Team', email_body)

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
            email.subject, "Blender Studio Subscription: payment failed (but we'll try again)"
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
            self.assertIn('Blender Studio Team', email_body)

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
        self.assertEqual(email.subject, 'Blender Studio Subscription: payment failed')
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
            self.assertIn('Blender Studio Team', email_body)

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
        self.assertEqual(email.subject, 'Blender Studio Subscription: payment received')
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
            self.assertIn('Blender Studio Team', email_body)

    def _assert_managed_subscription_notification_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['admin@example.com'])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Studio managed subscription needs attention')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(f'{user.customer.full_name} has', email_body)
            self.assertIn('its next payment date', email_body)
            self.assertIn('$\xa011.10', email_body)
            self.assertIn(
                f'/admin/looper/subscription/{subscription.pk}/change',
                email_body,
            )

    def _assert_subscription_expired_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [subscription.user.email])
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'We miss you at Blender Studio')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(f'Dear {user.customer.full_name}', email_body)
            self.assertIn(f'#{subscription.pk}', email_body)
            self.assertIn('has expired', email_body)
            self.assertIn(
                '/join/?source=subscription_expired_email',
                email_body,
            )
