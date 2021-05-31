import os
from unittest.mock import patch
import unittest

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time
from waffle.testutils import override_flag

from looper.tests.test_preferred_currency import EURO_IPV4, USA_IPV4, SINGAPORE_IPV4
from looper.money import Money
import looper.models

from common.tests.factories.subscriptions import create_customer_with_billing_address
from common.tests.factories.users import UserFactory
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
# **N.B.**: test cases below require settings.GEOIP2_DB to point to an existing GeoLite2 database.


def _get_default_variation(currency='USD'):
    return looper.models.Plan.objects.first().variation_for_currency(currency)


class _SharedAssertsMixin:
    def _assert_required_billing_details_updated(self, user):
        customer = user.customer
        address = customer.billing_address
        self.assertEqual(address.full_name, 'New Full Name')
        self.assertEqual(address.street_address, 'MAIN ST 1')
        self.assertEqual(address.locality, 'Amsterdam')
        self.assertEqual(address.postal_code, '1000 AA')
        self.assertEqual(address.country, 'NL')

        # self.assertEqual(address.extended_address, 'Floor 2')
        # self.assertEqual(address.company, 'Test LLC')

        # Check that customer fields were updated as well
        # self.assertEqual(customer.vat_number, 'NL818152011B01')
        # N.B.: email is saved as Customer.billing_email
        # self.assertEqual(customer.billing_email, 'my.billing.email@example.com')

    def _assert_billing_details_form_displayed(self, response):
        self.assertNotContains(response, 'Sign in with Blender ID')
        self.assertContains(response, 'Continue to payment')
        self.assertContains(response, 'id_street_address')
        self.assertContains(response, 'id_full_name')

    def _assert_payment_form_displayed(self, response):
        self.assertNotContains(response, 'Pricing has been updated')
        self.assertNotContains(response, 'Continue to payment')
        self.assertContains(response, 'Payment Method')
        self.assertContains(response, 'Confirm and pay')

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

    def _assert_plan_selector_with_sign_in_cta_displayed(self, response):
        self._assert_plan_selector_displayed(response)

        self.assertContains(response, 'Sign in with Blender ID')
        self.assertNotContains(response, 'Continue to payment')
        self.assertNotContains(response, 'id_street_address')
        self.assertNotContains(response, 'id_full_name')

    def _assert_default_variation_selected_no_tax_usd(self, response):
        self._assert_no_tax(response)
        self.assertContains(
            response,
            '<option selected data-first-renewal="June 19, 2021" data-currency-symbol="$" data-plan-id="1" data-price-recurring="$&nbsp;11.50&nbsp;/&nbsp;month" data-price="11.50" value="1">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">$&nbsp;11.50</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring">$&nbsp;11.50&nbsp;/&nbsp;month</span>',
            html=True,
        )

    def _assert_default_variation_selected_tax_21_eur(self, response):
        self.assertContains(
            response,
            '<option selected data-first-renewal="June 19, 2021" data-currency-symbol="€" data-plan-id="1" data-price-recurring="€&nbsp;9.90&nbsp;/&nbsp;month" data-price="9.90" data-price-tax="2.08" data-price-recurring-tax="2.08" data-tax-rate="21" data-tax-display-name="VAT" value="2">Every 1 month</option>',
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
        self.assertContains(
            response,
            '<span class="x-price-recurring">€&nbsp;9.90&nbsp;/&nbsp;month</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring-tax">Inc. 21% VAT (€&nbsp;2.08)</span>',
            html=True,
        )
        self.assertContains(
            response,
            'Renews <span class="x-first-renewal">June 19, 2021</span>',
            html=True,
        )

    def _assert_no_tax(self, response):
        self.assertNotContains(response, 'Inc. ')
        self.assertContains(
            response,
            '<span class="x-price-tax"></span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring-tax"></span>',
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
        self.assertContains(response, f'Blender Cloud order-{subscription.latest_order().pk}')

    def _assert_bank_transfer_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription Bank Payment')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn(
                f'Blender Cloud order-{subscription.latest_order().pk}',
                email_body,
            )
            self.assertIn('NL22 INGB 0005296212', email_body)
            self.assertIn('Dear Jane Doe,', email_body)
            self.assertIn('/settings/billing', email_body)
            self.assertIn('Manual renewal subscription', email_body)
            self.assertIn('€\xa014.90 per month', email_body)
            self.assertIn('Inc. 21% VAT', email_body)
            self.assertIn('is currently on hold', email_body)

    def _assert_subscription_activated_email_is_sent(self, subscription):
        user = subscription.user
        self.assertEqual(len(mail.outbox), 1)
        _write_mail(mail)
        email = mail.outbox[0]
        self.assertEqual(email.to, [user.email])
        # TODO(anna): set the correct reply_to
        self.assertEqual(email.reply_to, [])
        # TODO(anna): set the correct from_email DEFAULT_FROM_EMAIL
        self.assertEqual(email.from_email, 'webmaster@localhost')
        self.assertEqual(email.subject, 'Blender Cloud Subscription Activated')
        self.assertEqual(email.alternatives[0][1], 'text/html')
        for email_body in (email.body, email.alternatives[0][0]):
            self.assertIn('activated', email_body)
            self.assertIn('Dear Jane Doe,', email_body)
            self.assertIn('/settings/billing', email_body)
            self.assertIn('Automatic renewal subscription', email_body)
            self.assertIn('Blender Cloud Team', email_body)

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
        self.assertContains(response, 'is currently active')
        self.assertNotContains(response, 'Bank details')


@override_flag('SUBSCRIPTIONS_ENABLED', active=True)
@freeze_time('2021-05-19 11:41:11')
class TestGETJoinView(_CreateCustomerAndBillingAddressMixin, _SharedAssertsMixin, TestCase):
    url = reverse('subscriptions:join')

    def test_get_displays_plan_selection_with_tax_to_anonymous_nl(self):
        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_with_sign_in_cta_displayed(response)
        self._assert_default_variation_selected_tax_21_eur(response)

    def test_get_displays_plan_selection_without_tax_to_anonymous_us(self):
        response = self.client.get(self.url, REMOTE_ADDR=USA_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_with_sign_in_cta_displayed(response)
        self._assert_default_variation_selected_no_tax_usd(response)

    def test_get_prefills_full_name_and_billing_email_from_user(self):
        user = UserFactory(full_name="Jane До", email='jane.doe@example.com')
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_displayed(response)
        self.assertContains(
            response,
            '<input type="text" name="full_name" value="Jane До" maxlength="255" placeholder="Your Full Name" class="form-control" required id="id_full_name">',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="email" name="email" value="jane.doe@example.com" placeholder="mail@example.com" class="form-control" required id="id_email">',
            html=True,
        )

    def test_get_displays_plan_selection_and_billing_details_to_logged_in_nl(self):
        user = create_customer_with_billing_address(vat_number='', country='NL')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_billing_details_form_displayed(response)

        self._assert_plan_selector_displayed(response)
        self.assertContains(
            response,
            '<option selected data-first-renewal="June 19, 2021" data-currency-symbol="€" data-plan-id="1" data-price-recurring="€&nbsp;9.90&nbsp;/&nbsp;month" data-price-recurring-tax="2.08" data-price="9.90" data-price-tax="2.08" data-tax-rate="21" data-tax-display-name="VAT" value="2">Every 1 month</option>',
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
        self.assertContains(
            response,
            '<span class="x-price-recurring">€&nbsp;9.90&nbsp;/&nbsp;month</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring-tax">Inc. 21% VAT (€&nbsp;2.08)</span>',
            html=True,
        )

    def test_get_displays_plan_selection_and_billing_details_to_logged_in_de(self):
        user = create_customer_with_billing_address(vat_number='', country='DE')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_billing_details_form_displayed(response)

        self._assert_plan_selector_displayed(response)
        self.assertContains(
            response,
            '<option selected data-first-renewal="June 19, 2021" data-currency-symbol="€" data-plan-id="1" data-price-recurring="€&nbsp;9.90&nbsp;/&nbsp;month" data-price="9.90" data-price-tax="1.88" data-price-recurring-tax="1.88" data-tax-rate="19" data-tax-display-name="VAT" value="2">Every 1 month</option>',
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
        self.assertContains(
            response,
            '<span class="x-price-recurring">€&nbsp;9.90&nbsp;/&nbsp;month</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring-tax">Inc. 19% VAT (€&nbsp;1.88)</span>',
            html=True,
        )

    def test_get_displays_plan_selection_and_billing_details_to_logged_in_us(self):
        user = create_customer_with_billing_address(
            vat_number='', country='US', region='NY', postal_code='12001'
        )
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self._assert_billing_details_form_displayed(response)
        self._assert_form_us_address_is_displayed(response)

        self._assert_plan_selector_displayed(response)
        # Check there's no tax on the displayed options
        self._assert_no_tax(response)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_us_sets_preferred_currency_usd(self):
        user = create_customer_with_billing_address()
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=USA_IPV4)

        self.assertEqual(response.status_code, 200)
        # Check that country is preselected
        self.assertContains(
            response,
            '<option value="US" selected>United States of America</option>',
            html=True,
        )
        # Check that prices are in USD and there is not tax
        self._assert_default_variation_selected_no_tax_usd(response)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_sg_sets_preferred_currency_usd(self):
        user = create_customer_with_billing_address()
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=SINGAPORE_IPV4)

        self.assertEqual(response.status_code, 200)
        # Check that country is preselected
        self.assertContains(
            response,
            '<option value="SG" selected>Singapore</option>',
            html=True,
        )
        # Check that prices are in USD and there is not tax
        self._assert_default_variation_selected_no_tax_usd(response)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_nl_sets_preferred_currency_eur(self):
        user = create_customer_with_billing_address()
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        # Check that country is preselected
        self.assertContains(
            response,
            '<option value="NL" selected>Netherlands</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option selected data-first-renewal="June 19, 2021" data-currency-symbol="€" data-plan-id="1" data-price-recurring="€&nbsp;9.90&nbsp;/&nbsp;month" data-price="9.90" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;9.90</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring">€&nbsp;9.90&nbsp;/&nbsp;month</span>',
            html=True,
        )


@override_flag('SUBSCRIPTIONS_ENABLED', active=True)
@freeze_time('2021-05-19 11:41:11')
class TestPOSTJoinView(_CreateCustomerAndBillingAddressMixin, _SharedAssertsMixin, TestCase):
    url = reverse('subscriptions:join')

    def test_post_updates_billing_address_and_customer_renders_next_form_de(self):
        user = create_customer_with_billing_address(vat_number='', country='DE')
        self.client.force_login(user)

        selected_variation = (
            looper.models.PlanVariation.objects.active()
            .filter(
                collection_method='manual',
            )
            .first()
        )
        data = {
            **required_address_data,
            'plan_variation_id': selected_variation.id,
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)

        self._assert_required_billing_details_updated(user)
        # Check that a warning message is displayed
        self._assert_pricing_has_been_updated(response)

        # Check that the manual plan variation is still selected
        self.assertContains(
            response,
            '<option selected value="2" title="This subscription is renewed manually. You can leave it on-hold, or renew it when convenient.">Manual renewal</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<option selected data-first-renewal="May 19, 2022" data-currency-symbol="€" data-plan-id="2" data-price-recurring="€&nbsp;119&nbsp;/&nbsp;year" data-price="119.00" data-price-tax="24.99" data-price-recurring-tax="24.99" data-tax-rate="21" data-tax-display-name="VAT" value="14">Every 1 year</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;119.00</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;24.99)</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring">€&nbsp;119&nbsp;/&nbsp;year</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring-tax">Inc. 21% VAT (€&nbsp;24.99)</span>',
            html=True,
        )
        self.assertContains(
            response,
            'Renews <span class="x-first-renewal">May 19, 2022</span>',
            html=True,
        )
        self.assertEqual(
            response.context['form'].cleaned_data['plan_variation_id'], selected_variation.pk
        )

    def test_post_has_correct_price_field_value(self):
        self.client.force_login(self.user)

        default_variation = _get_default_variation('EUR')
        data = {
            **required_address_data,
            'plan_variation_id': default_variation.pk,
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        # Check that we are no longer on the billing details page
        self._assert_payment_form_displayed(response)

        self._assert_default_variation_selected_tax_21_eur(response)
        # The hidden price field must also be set to a matching amount
        self.assertContains(
            response,
            '<input type="hidden" name="price" value="9.90" class="form-control" id="id_price">',
            html=True,
        )

    def test_post_updates_billing_address_and_customer_applies_reverse_charged_tax(self):
        self.client.force_login(self.user)

        default_variation = _get_default_variation('EUR')
        data = {
            **required_address_data,
            'vat_number': 'DE 260543043',
            'country': 'DE',
            'postal_code': '11111',
            'plan_variation_id': default_variation.id,
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.customer.vat_number, 'DE 260543043')
        address = self.user.customer.billing_address
        self.assertEqual(address.full_name, 'New Full Name')
        self.assertEqual(address.postal_code, '11111')
        self.assertEqual(address.country, 'DE')

        # Check that a warning message is displayed
        self._assert_pricing_has_been_updated(response)

        # Check that default plan variation with subtracted VAT is displayed, and no tax is displayed
        self._assert_no_tax(response)
        self.assertContains(
            response,
            '<option selected data-first-renewal="June 19, 2021" data-currency-symbol="€" data-plan-id="1" data-price-recurring="€&nbsp;8.02&nbsp;/&nbsp;month" data-price="8.02" value="2">Every 1 month</option>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price">€&nbsp;8.02</span>',
            html=True,
        )
        self.assertContains(
            response,
            '<span class="x-price-recurring">€&nbsp;8.02&nbsp;/&nbsp;month</span>',
            html=True,
        )

        # Post the same form again
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        # Check that we are no longer on the billing details page
        self._assert_payment_form_displayed(response)

        # The hidden price field must also be set to a matching amount
        self.assertContains(
            response,
            '<input type="hidden" name="price" value="8.02" class="form-control" id="id_price">',
            html=True,
        )

    def test_post_changing_address_from_with_region_to_without_region_clears_region(self):
        user = create_customer_with_billing_address(
            vat_number='', country='US', region='NY', postal_code='12001'
        )
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.customer.billing_address.region, 'NY')
        self._assert_billing_details_form_displayed(response)
        self._assert_form_us_address_is_displayed(response)
        self._assert_plan_selector_displayed(response)
        self._assert_no_tax(response)

        # Post an new address that doesn't require a region
        default_variation = _get_default_variation('EUR')
        data = {
            **required_address_data,
            'country': 'DE',
            'postal_code': '11111',
            'plan_variation_id': default_variation.id,
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)

        self._assert_pricing_has_been_updated(response)

        self.assertEqual(user.customer.billing_address.full_name, 'New Full Name')
        # Check that billing details has been updated correctly
        self.assertEqual(user.customer.billing_address.region, '')
        self.assertEqual(user.customer.billing_address.country, 'DE')
        self.assertEqual(user.customer.billing_address.postal_code, '11111')


@override_flag('SUBSCRIPTIONS_ENABLED', active=True)
@freeze_time('2021-05-19 11:41:11')
class TestPOSTJoinConfirmAndPayView(
    _CreateCustomerAndBillingAddressMixin, _SharedAssertsMixin, TestCase
):
    url = reverse('subscriptions:join-confirm-and-pay')

    def test_invalid_missing_required_fields(self):
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        data = required_address_data
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_displayed(response)
        self._assert_default_variation_selected_tax_21_eur(response)
        self.assertEqual(
            response.context['form'].errors,
            {
                'gateway': ['This field is required.'],
                'payment_method_nonce': ['This field is required.'],
                'plan_variation_id': ['This field is required.'],
                'price': ['This field is required.'],
            },
        )

    def test_invalid_price_does_not_match_selected_plan_variation(self):
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        selected_variation = _get_default_variation('EUR')
        data = {
            **required_address_data,
            'gateway': 'braintree',
            'payment_method_nonce': 'fake-valid-nonce',
            'plan_variation_id': selected_variation.id,
            'price': '999.09',
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_displayed(response)
        self._assert_default_variation_selected_tax_21_eur(response)
        self.assertEqual(
            response.context['form'].cleaned_data['plan_variation_id'], selected_variation.pk
        )
        self.assertEqual(
            response.context['form'].errors,
            {'__all__': ['Payment failed: please reload the page and try again']},
        )

    def test_invalid_bank_transfer_cannot_be_selected_for_automatic_payments(self):
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        selected_variation = _get_default_variation('EUR')
        data = {
            **required_address_data,
            'gateway': 'bank',
            'payment_method_nonce': 'unused',
            'plan_variation_id': selected_variation.id,
            'price': '9.90',
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors,
            {
                'gateway': [
                    'Select a valid choice. That choice is not one of the available choices.'
                ]
            },
        )

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_bank_transfer_required',
        new=subscriptions.tasks.send_mail_bank_transfer_required.task_function,
    )
    def test_pay_with_bank_transfer_creates_order_subscription_on_hold(self):
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.client.force_login(user)

        selected_variation = (
            looper.models.PlanVariation.objects.active()
            .filter(
                collection_method='manual',
                currency='EUR',
                interval_length=1,
                interval_unit='month',
            )
            .first()
        )
        data = {
            **required_address_data,
            'gateway': 'bank',
            'payment_method_nonce': 'unused',
            'plan_variation_id': selected_variation.id,
            'price': '14.90',
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_transactionless_done_page_displayed(response)

        subscription = user.subscription_set.first()
        self.assertEqual(subscription.status, 'on-hold')
        self.assertEqual(subscription.price, Money('EUR', 1490))
        self.assertEqual(subscription.tax, Money('EUR', 313))
        self.assertEqual(subscription.tax_country, 'NL')
        self.assertEqual(subscription.tax_type, 'VATC')
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'manual')
        self.assertEqual(subscription.plan, selected_variation.plan)

        order = subscription.latest_order()
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.price, Money('EUR', 1490))
        self.assertEqual(order.tax, Money('EUR', 313))
        self.assertEqual(order.tax_country, 'NL')
        self.assertEqual(order.tax_type, 'VATC')

        self._assert_bank_transfer_email_is_sent(subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_subscription_status_changed',
        new=subscriptions.tasks.send_mail_subscription_status_changed.task_function,
    )
    def test_pay_with_credit_card_creates_order_subscription_active(self):
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.client.force_login(user)

        selected_variation = _get_default_variation('EUR')
        data = {
            **required_address_data,
            'gateway': 'braintree',
            # fake-three-d-secure-visa-full-authentication-nonce
            # causes the following error:
            # Merchant account must match the 3D Secure authorization merchant account: code 91584
            # TODO(anna): figure out if this is due to our settings or a quirk of the sandbox
            'payment_method_nonce': 'fake-valid-nonce',
            'plan_variation_id': selected_variation.id,
            'price': '9.90',
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_done_page_displayed(response)

        subscription = user.subscription_set.first()
        order = subscription.latest_order()
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.price, Money('EUR', 990))
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'automatic')
        self.assertEqual(subscription.plan, selected_variation.plan)
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.price, Money('EUR', 990))

        self._assert_subscription_activated_email_is_sent(subscription)

    def test_pay_with_credit_card_creates_order_subscription_active_business_de(self):
        user = create_customer_with_billing_address(country='DE', vat_number='DE 260543043')
        self.client.force_login(user)

        selected_variation = (
            looper.models.PlanVariation.objects.active()
            .filter(
                collection_method='manual',
                currency='EUR',
                interval_length=1,
                interval_unit='month',
            )
            .first()
        )
        data = {
            **required_address_data,
            'vat_number': 'DE 260543043',
            'country': 'DE',
            'postal_code': '11111',
            'gateway': 'braintree',
            'payment_method_nonce': 'fake-valid-nonce',
            'plan_variation_id': selected_variation.id,
            # VAT is subtracted from the plan variation price:
            'price': '12.07',
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_done_page_displayed(response)

        subscription = user.subscription_set.first()
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.price, Money('EUR', 1490))
        self.assertEqual(subscription.tax, Money('EUR', 0))
        self.assertEqual(subscription.tax_country, 'DE')
        self.assertEqual(subscription.tax_rate, 19)
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'manual')
        self.assertEqual(subscription.plan, selected_variation.plan)
        self.assertEqual(subscription.currency, 'EUR')
        self.assertEqual(subscription.interval_unit, 'month')
        self.assertEqual(subscription.interval_length, 1)

        order = subscription.latest_order()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.price, Money('EUR', 1207))
        self.assertEqual(order.tax, Money('EUR', 0))
        self.assertEqual(order.vat_number, 'DE 260543043')
        self.assertEqual(order.tax_country, 'DE')
        self.assertEqual(order.tax_rate, 19)


class TestJoinRedirectsWithoutFlagView(_CreateCustomerAndBillingAddressMixin, TestCase):
    def test_join_get_redirects_to_store_anonymous(self):
        response = self.client.get(reverse('subscriptions:join'), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], settings.STORE_PRODUCT_URL)

    def test_join_post_redirects_to_store_anonymous(self):
        response = self.client.post(reverse('subscriptions:join'), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], settings.STORE_PRODUCT_URL)

    def test_join_get_redirects_to_store(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('subscriptions:join'), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], settings.STORE_PRODUCT_URL)

    def test_join_post_redirects_to_store(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('subscriptions:join'), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], settings.STORE_PRODUCT_URL)

    def test_join_confirm_get_redirects_to_store(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('subscriptions:join-confirm-and-pay'), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], settings.STORE_PRODUCT_URL)

    def test_join_confirm_post_redirects_to_store(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('subscriptions:join-confirm-and-pay'), {})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], settings.STORE_PRODUCT_URL)


class TestJoinConfirmAndPayLoggedInUserOnlyView(_CreateCustomerAndBillingAddressMixin, TestCase):
    def test_get_anonymous_403(self):
        response = self.client.get(reverse('subscriptions:join-confirm-and-pay'), {})

        self.assertEqual(response.status_code, 403)

    def test_join_post_anonymous_403(self):
        response = self.client.post(reverse('subscriptions:join-confirm-and-pay'), {})

        self.assertEqual(response.status_code, 403)
