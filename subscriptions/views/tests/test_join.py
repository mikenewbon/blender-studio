from typing import Tuple
from unittest.mock import patch
import os
import unittest

from django.conf import settings
from django.urls import reverse
from freezegun import freeze_time
import responses

from looper.tests.test_preferred_currency import EURO_IPV4, USA_IPV4, SINGAPORE_IPV4
from looper.money import Money
import looper.models

from common.tests.factories.subscriptions import create_customer_with_billing_address
from common.tests.factories.users import UserFactory
from subscriptions.tests.base import BaseSubscriptionTestCase
import subscriptions.tasks
import users.tasks
import users.tests.util as util

required_address_data = {
    'country': 'NL',
    'email': 'my.billing.email@example.com',
    'full_name': 'New Full Name',
    'postal_code': '1000 AA',
}
full_billing_address_data = {
    **required_address_data,
    'street_address': 'MAIN ST 1',
    'locality': 'Amsterdam',
    'extended_address': 'Floor 2',
    'company': 'Test LLC',
    'vat_number': 'NL818152011B01',
}
# **N.B.**: test cases below require settings.GEOIP2_DB to point to an existing GeoLite2 database.


def _get_default_variation(currency='USD'):
    return looper.models.Plan.objects.first().variation_for_currency(currency)


@freeze_time('2021-05-19 11:41:11')
class TestGETBillingDetailsView(BaseSubscriptionTestCase):
    url_usd = reverse('subscriptions:join-billing-details', kwargs={'plan_variation_id': 1})
    url = reverse('subscriptions:join-billing-details', kwargs={'plan_variation_id': 2})

    def test_get_prefills_full_name_and_billing_email_from_user(self):
        user = UserFactory(full_name="Jane До", email='jane.doe@example.com')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_total_default_variation_selected_tax_21_eur(response)
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

    def test_get_displays_total_and_billing_details_to_logged_in_nl(self):
        user = create_customer_with_billing_address(vat_number='', country='NL')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_billing_details_form_displayed(response)

        self._assert_total_default_variation_selected_tax_21_eur(response)

    def test_get_displays_total_and_billing_details_to_logged_in_de(self):
        user = create_customer_with_billing_address(vat_number='', country='DE')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_billing_details_form_displayed(response)
        self._assert_total_default_variation_selected_tax_19_eur(response)

    def test_get_displays_total_and_billing_details_to_logged_in_us(self):
        user = create_customer_with_billing_address(
            vat_number='', country='US', region='NY', postal_code='12001'
        )
        self.client.force_login(user)

        response = self.client.get(self.url_usd)

        self.assertEqual(response.status_code, 200)
        self._assert_billing_details_form_displayed(response)
        self._assert_form_us_address_is_displayed(response)
        self._assert_total_default_variation_selected_usd(response)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_us_sets_preferred_currency_usd_invalid_variation(self):
        user = create_customer_with_billing_address()
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=USA_IPV4)
        self.assertEqual(response.status_code, 404)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_us_sets_preferred_currency_usd(self):
        user = create_customer_with_billing_address()
        self.client.force_login(user)

        response = self.client.get(self.url_usd, REMOTE_ADDR=USA_IPV4)

        self.assertEqual(response.status_code, 200)
        # Check that country is preselected
        self.assertContains(
            response,
            '<option value="US" selected>United States of America</option>',
            html=True,
        )
        # Check that prices are in USD and there is no tax
        self._assert_total_default_variation_selected_usd(response)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_sg_sets_preferred_currency_eur(self):
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
        # Check that prices are in EUR and there is no tax
        self._assert_total_default_variation_selected_no_tax_eur(response)

    @unittest.skipUnless(os.path.exists(settings.GEOIP2_DB), 'GeoIP database file is required')
    def test_get_detects_country_nl_sets_preferred_currency_eur_displays_correct_vat(self):
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
        self._assert_total_default_variation_selected_tax_21_eur(response)


@freeze_time('2021-05-19 11:41:11')
class TestPOSTBillingDetailsView(BaseSubscriptionTestCase):
    url_usd = reverse('subscriptions:join-billing-details', kwargs={'plan_variation_id': 1})
    url = reverse('subscriptions:join-billing-details', kwargs={'plan_variation_id': 2})

    def test_post_updates_billing_address_and_customer_renders_next_form_de(self):
        user = create_customer_with_billing_address(vat_number='', country='DE')
        self.client.force_login(user)

        selected_variation = (
            looper.models.PlanVariation.objects.active()
            .filter(
                currency='EUR',
                plan__name='Manual renewal',
            )
            .first()
        )
        data = full_billing_address_data
        url = reverse(
            'subscriptions:join-billing-details',
            kwargs={'plan_variation_id': selected_variation.pk},
        )
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)

        self._assert_required_billing_details_updated(user)
        # Check that a warning message is displayed
        self._assert_pricing_has_been_updated(response)

        self._assert_continue_to_payment_displayed(response)
        # Check that the manual plan variation totals are displayed
        self.assertContains(response, 'Total')
        self.assertContains(
            response, '<span class="x-price-tax">Inc. 21% VAT (€&nbsp;20.65)</span>', html=True
        )
        self.assertContains(response, '<span class="x-price">€&nbsp;119.00</span>', html=True)
        self.assertContains(response, 'Manual ')
        self.assertContains(response, '/ <span class="x-price-period">1 year</span>', html=True)

    def test_post_has_correct_price_field_value(self):
        self.client.force_login(self.user)

        default_variation = _get_default_variation('EUR')
        data = required_address_data
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            reverse(
                'subscriptions:join-confirm-and-pay',
                kwargs={'plan_variation_id': default_variation.pk},
            ),
        )

        # Follow the redirect to avoid "Couldn't retrieve content: Response code was 302 (expected 200)"
        response = self.client.get(response['Location'])
        # Check that we are no longer on the billing details page
        self._assert_payment_form_displayed(response)

        self._assert_total_default_variation_selected_tax_21_eur(response)
        # The hidden price field must also be set to a matching amount
        self.assertContains(
            response,
            '<input type="hidden" name="price" value="9.90" class="form-control" id="id_price">',
            html=True,
        )

    def test_post_updates_billing_address_and_customer_applies_reverse_charged_tax(self):
        self.client.force_login(self.user)

        data = {
            **required_address_data,
            'vat_number': 'DE 260543043',
            'country': 'DE',
            'postal_code': '11111',
        }
        response = self.client.post(self.url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.customer.vat_number, 'DE260543043')
        address = self.user.customer.billing_address
        self.assertEqual(address.full_name, 'New Full Name')
        self.assertEqual(address.postal_code, '11111')
        self.assertEqual(address.country, 'DE')

        # Check that a warning message is displayed
        self._assert_pricing_has_been_updated(response)

        # Check that default plan variation with subtracted VAT is displayed, and no tax is displayed
        self._assert_total_default_variation_selected_tax_19_eur_reverse_charged(response)

        # Post the same form again
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        # Follow the redirect to avoid unexpected assertion errors
        response = self.client.get(response['Location'])

        # Check that we are no longer on the billing details page
        self._assert_payment_form_displayed(response)

        # The hidden price field must also be set to a matching amount
        self.assertContains(
            response,
            '<input type="hidden" name="price" value="8.32" class="form-control" id="id_price">',
            html=True,
        )

    def test_post_changing_address_from_with_region_to_without_region_clears_region(self):
        user = create_customer_with_billing_address(
            vat_number='', country='US', region='NY', postal_code='12001'
        )
        self.client.force_login(user)

        response = self.client.get(self.url_usd)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.customer.billing_address.region, 'NY')
        self._assert_billing_details_form_displayed(response)
        self._assert_form_us_address_is_displayed(response)
        self._assert_total_default_variation_selected_usd(response)

        # Post an new address that doesn't require a region
        data = {
            **required_address_data,
            'country': 'DE',
            'postal_code': '11111',
        }
        response = self.client.post(self.url_usd, data)

        self.assertEqual(response.status_code, 302)
        # Redirected to the plan variation with matching currency
        self.assertEqual(response['Location'], self.url)
        # Follow redirect to be able to assert contents of it
        response = self.client.get(response['Location'])

        self._assert_pricing_has_been_updated(response)

        self.assertEqual(user.customer.billing_address.full_name, 'New Full Name')
        # Check that billing details has been updated correctly
        self.assertEqual(user.customer.billing_address.region, '')
        self.assertEqual(user.customer.billing_address.country, 'DE')
        self.assertEqual(user.customer.billing_address.postal_code, '11111')


@freeze_time('2021-05-19 11:41:11')
class TestPOSTConfirmAndPayView(BaseSubscriptionTestCase):
    def _get_url_for(self, **filter_params) -> Tuple[str, looper.models.PlanVariation]:
        plan_variation = looper.models.PlanVariation.objects.active().get(**filter_params)
        return (
            reverse(
                'subscriptions:join-confirm-and-pay',
                kwargs={'plan_variation_id': plan_variation.pk},
            ),
            plan_variation,
        )

    def test_plan_variation_does_not_match_detected_currency_usd_euro_ip(self):
        url, _ = self._get_url_for(currency='USD', price=11900)
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        data = required_address_data
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 404)

    def test_plan_variation_matches_detected_currency_eur_non_eea_ip(self):
        url, _ = self._get_url_for(currency='EUR', price=990)
        user = create_customer_with_billing_address()
        self.client.force_login(user)

        data = required_address_data
        response = self.client.post(url, data, REMOTE_ADDR=SINGAPORE_IPV4)

        self.assertEqual(response.status_code, 200)
        # Check that prices are in EUR and there is no tax
        self._assert_total_default_variation_selected_no_tax_eur(response)

    def test_billing_address_country_takes_precedence_over_geo_ip(self):
        url, _ = self._get_url_for(currency='EUR', price=990)
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        data = required_address_data
        response = self.client.post(url, data, REMOTE_ADDR=SINGAPORE_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_total_default_variation_selected_tax_21_eur(response)

    def test_invalid_missing_required_fields(self):
        url, _ = self._get_url_for(currency='EUR', price=990)
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        data = required_address_data
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_total_default_variation_selected_tax_21_eur(response)
        self.assertEqual(
            response.context['form'].errors,
            {
                'gateway': ['This field is required.'],
                'payment_method_nonce': ['This field is required.'],
                'price': ['This field is required.'],
            },
        )

    def test_invalid_price_does_not_match_selected_plan_variation(self):
        url, selected_variation = self._get_url_for(currency='EUR', price=990)
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        data = {
            **required_address_data,
            'gateway': 'braintree',
            'payment_method_nonce': 'fake-valid-nonce',
            'price': '999.09',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_total_default_variation_selected_tax_21_eur(response)
        self.assertEqual(
            response.context['form'].errors,
            {'__all__': ['Payment failed: please reload the page and try again']},
        )

    def test_invalid_bank_transfer_cannot_be_selected_for_automatic_payments(self):
        url, selected_variation = self._get_url_for(currency='EUR', price=990)
        user = create_customer_with_billing_address(country='NL')
        self.client.force_login(user)

        data = {
            **required_address_data,
            'gateway': 'bank',
            'payment_method_nonce': 'unused',
            'price': '9.90',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

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
    @patch(
        'users.signals.tasks.grant_blender_id_role',
        new=users.tasks.grant_blender_id_role.task_function,
    )
    @responses.activate
    def test_pay_with_bank_transfer_creates_order_subscription_on_hold(self):
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.client.force_login(user)
        util.mock_blender_id_badger_badger_response(
            'grant', 'cloud_has_subscription', user.oauth_info.oauth_user_id
        )

        url, selected_variation = self._get_url_for(
            currency='EUR',
            interval_length=1,
            interval_unit='month',
            plan__name='Manual renewal',
        )
        data = {
            **required_address_data,
            'gateway': 'bank',
            'payment_method_nonce': 'unused',
            'price': '14.90',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_transactionless_done_page_displayed(response)

        subscription = user.subscription_set.first()
        self.assertEqual(subscription.status, 'on-hold')
        self.assertEqual(subscription.price, Money('EUR', 1490))
        self.assertEqual(subscription.tax, Money('EUR', 259))
        self.assertEqual(subscription.tax_country, 'NL')
        self.assertEqual(subscription.tax_type, 'VATC')
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'manual')
        self.assertEqual(subscription.plan, selected_variation.plan)

        order = subscription.latest_order()
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.price, Money('EUR', 1490))
        self.assertEqual(order.tax, Money('EUR', 259))
        self.assertEqual(order.tax_country, 'NL')
        self.assertEqual(order.tax_type, 'VATC')
        self.assertIsNotNone(order.pk)
        self.assertIsNotNone(order.number)
        self.assertIsNotNone(order.display_number)
        self.assertNotEqual(order.display_number, str(order.pk))

        self._assert_bank_transfer_email_is_sent(subscription)
        self._assert_bank_transfer_email_is_sent_tax_21(subscription)

        # Check that the reverse-charged price is displayed in billing as well
        response = self.client.get(
            reverse('subscriptions:manage', kwargs={'subscription_id': subscription.pk})
        )
        self.assertContains(response, f'Subscription #{subscription.pk}', html=True)
        self.assertContains(response, 'Subscription On Hold', html=True)
        self.assertContains(response, 'Bank Transfer', html=True)
        self.assertContains(response, '€\xa014.90\u00A0/\u00A0month', html=True)
        # Check that bank details are displayed
        self.assertContains(
            response,
            'Blender Studio B.V.\n'
            'Bank: ING Bank\n'
            'IBAN: NL07 INGB 0008 4489 82\n'
            'BIC/Swift: INGB NL2A\n',
            html=True,
        )
        self.assertContains(response, f'Blender Studio order-{order.number}', html=True)

    @patch(
        'subscriptions.signals.tasks.send_mail_bank_transfer_required',
        new=subscriptions.tasks.send_mail_bank_transfer_required.task_function,
    )
    @patch(
        'users.signals.tasks.grant_blender_id_role',
        new=users.tasks.grant_blender_id_role.task_function,
    )
    @responses.activate
    def test_pay_with_bank_transfer_creates_order_subscription_on_hold_shows_reverse_charged_price(
        self,
    ):
        user = create_customer_with_billing_address(
            country='ES', full_name='Jane Doe', vat_number='DE260543043'
        )
        self.client.force_login(user)
        util.mock_blender_id_badger_badger_response(
            'grant', 'cloud_has_subscription', user.oauth_info.oauth_user_id
        )

        url, selected_variation = self._get_url_for(
            currency='EUR',
            plan__name='Manual renewal',
            interval_length=3,
            interval_unit='month',
        )
        data = {
            **required_address_data,
            'gateway': 'bank',
            'payment_method_nonce': 'unused',
            'price': '26.45',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_transactionless_done_page_displayed(response)

        subscription = user.subscription_set.first()
        self.assertEqual(subscription.status, 'on-hold')
        self.assertEqual(subscription.price, Money('EUR', 3200))
        self.assertEqual(subscription.tax, Money('EUR', 0))
        self.assertEqual(subscription.tax_country, 'ES')
        self.assertEqual(subscription.tax_type, 'VATRC')
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'manual')
        self.assertEqual(subscription.plan, selected_variation.plan)

        order = subscription.latest_order()
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.price, Money('EUR', 2645))
        self.assertEqual(order.tax, Money('EUR', 0))
        self.assertEqual(order.tax_country, 'ES')
        self.assertEqual(order.tax_type, 'VATRC')
        self.assertIsNotNone(order.pk)
        self.assertIsNotNone(order.number)
        self.assertIsNotNone(order.display_number)
        self.assertIsNotNone(order.vat_number)
        self.assertNotEqual(order.display_number, str(order.pk))

        self._assert_bank_transfer_email_is_sent(subscription)
        self._assert_bank_transfer_email_is_sent_tax_21_eur_reverse_charged(subscription)

        # Check that the reverse-charged price is displayed in billing as well
        response = self.client.get(
            reverse('subscriptions:manage', kwargs={'subscription_id': subscription.pk})
        )
        self.assertNotIn('32.00', response)
        self.assertNotIn('21%', response)
        self.assertNotIn('Inc.', response)
        self.assertNotIn('VAT', response)
        self.assertContains(response, f'Subscription #{subscription.pk}', html=True)
        self.assertContains(response, 'Subscription On Hold', html=True)
        self.assertContains(response, 'Bank Transfer', html=True)
        self.assertContains(response, '€\xa026.45\u00A0/\u00A0quarter', html=True)
        # Check that bank details are displayed
        self.assertContains(
            response,
            'Blender Studio B.V.\n'
            'Bank: ING Bank\n'
            'IBAN: NL07 INGB 0008 4489 82\n'
            'BIC/Swift: INGB NL2A\n',
            html=True,
        )
        self.assertContains(response, f'Blender Studio order-{order.number}', html=True)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_subscription_status_changed',
        new=subscriptions.tasks.send_mail_subscription_status_changed.task_function,
    )
    @patch(
        'users.signals.tasks.grant_blender_id_role',
        new=users.tasks.grant_blender_id_role.task_function,
    )
    @responses.activate
    def test_pay_with_credit_card_creates_order_subscription_active(self):
        url, selected_variation = self._get_url_for(currency='EUR', price=990)
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.client.force_login(user)
        util.mock_blender_id_badger_badger_response(
            'grant', 'cloud_has_subscription', user.oauth_info.oauth_user_id
        )
        util.mock_blender_id_badger_badger_response(
            'grant', 'cloud_subscriber', user.oauth_info.oauth_user_id
        )

        data = {
            **required_address_data,
            'gateway': 'braintree',
            # fake-three-d-secure-visa-full-authentication-nonce
            # causes the following error:
            # Merchant account must match the 3D Secure authorization merchant account: code 91584
            # TODO(anna): figure out if this is due to our settings or a quirk of the sandbox
            'payment_method_nonce': 'fake-valid-nonce',
            'price': '9.90',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_done_page_displayed(response)

        subscription = user.subscription_set.first()
        order = subscription.latest_order()
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.price, Money('EUR', 990))
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'automatic')
        self.assertEqual(subscription.plan, selected_variation.plan)
        self.assertEqual(order.status, 'paid')
        self.assertIsNotNone(order.number)
        self.assertEqual(order.price, Money('EUR', 990))

        self._assert_subscription_activated_email_is_sent(subscription)

    @patch(
        # Make sure background task is executed as a normal function
        'subscriptions.signals.tasks.send_mail_subscription_status_changed',
        new=subscriptions.tasks.send_mail_subscription_status_changed.task_function,
    )
    @patch(
        'users.signals.tasks.grant_blender_id_role',
        new=users.tasks.grant_blender_id_role.task_function,
    )
    @responses.activate
    def test_pay_with_credit_card_creates_order_subscription_active_team(self):
        url, selected_variation = self._get_url_for(
            currency='EUR',
            price=9000,
            plan__name='Automatic renewal, 15 seats',
        )
        user = create_customer_with_billing_address(country='NL', full_name='Jane Doe')
        self.client.force_login(user)
        util.mock_blender_id_badger_badger_response(
            'grant', 'cloud_has_subscription', user.oauth_info.oauth_user_id
        )
        util.mock_blender_id_badger_badger_response(
            'grant', 'cloud_subscriber', user.oauth_info.oauth_user_id
        )

        data = {
            **required_address_data,
            'gateway': 'braintree',
            'payment_method_nonce': 'fake-valid-nonce',
            'price': '90.00',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

        self._assert_done_page_displayed(response)

        subscription = user.subscription_set.first()
        order = subscription.latest_order()
        self.assertEqual(subscription.status, 'active')
        self.assertEqual(subscription.price, Money('EUR', 9000))
        self.assertEqual(subscription.collection_method, selected_variation.collection_method)
        self.assertEqual(subscription.collection_method, 'automatic')
        self.assertEqual(subscription.plan, selected_variation.plan)
        self.assertEqual(order.status, 'paid')
        self.assertIsNotNone(order.number)
        self.assertEqual(order.price, Money('EUR', 9000))
        self.assertEqual(order.subscription.team.seats, 15)

        self._assert_team_subscription_activated_email_is_sent(subscription)

    def test_pay_with_credit_card_creates_order_subscription_active_business_de(self):
        user = create_customer_with_billing_address(country='DE', vat_number='DE260543043')
        self.client.force_login(user)

        url, selected_variation = self._get_url_for(
            currency='EUR',
            interval_length=1,
            interval_unit='month',
            plan__name='Manual renewal',
        )
        data = {
            **required_address_data,
            'vat_number': 'DE 260543043',
            'country': 'DE',
            'postal_code': '11111',
            'gateway': 'braintree',
            'payment_method_nonce': 'fake-valid-nonce',
            # VAT is subtracted from the plan variation price:
            'price': '12.52',
        }
        response = self.client.post(url, data, REMOTE_ADDR=EURO_IPV4)

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
        self.assertEqual(order.price, Money('EUR', 1252))
        self.assertEqual(order.tax, Money('EUR', 0))
        self.assertEqual(order.vat_number, 'DE260543043')
        self.assertEqual(order.tax_country, 'DE')
        self.assertEqual(order.tax_rate, 19)
        self.assertIsNotNone(order.number)


class TestJoinConfirmAndPayLoggedInUserOnlyView(BaseSubscriptionTestCase):
    url = reverse('subscriptions:join-confirm-and-pay', kwargs={'plan_variation_id': 8})

    def test_get_anonymous_403(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_join_post_anonymous_403(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
