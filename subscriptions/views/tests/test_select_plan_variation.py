from django.urls import reverse
from freezegun import freeze_time

from looper.tests.test_preferred_currency import EURO_IPV4, USA_IPV4  # , SINGAPORE_IPV4

from common.tests.factories.subscriptions import create_customer_with_billing_address
from subscriptions.tests.base import BaseSubscriptionTestCase

EURO_FR_IPV4 = '92.147.188.130'


@freeze_time('2021-05-19 11:41:11')
class TestSelectPlanVariationView(BaseSubscriptionTestCase):
    url = reverse('subscriptions:join')
    url_team = reverse('subscriptions:join-team')

    def test_get_displays_plan_selection_with_tax_to_anonymous_nl(self):
        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_with_sign_in_cta_displayed(response)
        self._assert_default_variation_selected_tax_21_eur(response)

    def test_get_team_displays_plan_selection_with_tax_to_anonymous_nl(self):
        response = self.client.get(self.url_team, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_team_plan_selector_with_sign_in_cta_displayed(response)
        self._assert_default_team_variation_selected_tax_21_eur(response)

    def test_get_displays_plan_selection_with_tax_to_anonymous_fr(self):
        response = self.client.get(self.url, REMOTE_ADDR=EURO_FR_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_with_sign_in_cta_displayed(response)
        self._assert_default_variation_selected_tax_20_eur(response)

    def test_get_displays_plan_selection_without_tax_to_anonymous_us(self):
        response = self.client.get(self.url, REMOTE_ADDR=USA_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_with_sign_in_cta_displayed(response)
        self._assert_default_variation_selected_no_tax_usd(response)

    def test_get_displays_plan_selection_to_logged_in_nl(self):
        user = create_customer_with_billing_address(vat_number='', country='NL')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_displayed(response)
        self._assert_continue_to_billing_displayed(response)
        self._assert_default_variation_selected_tax_21_eur(response)

    def test_get_displays_plan_selection_to_logged_in_de(self):
        user = create_customer_with_billing_address(vat_number='', country='DE')
        self.client.force_login(user)

        response = self.client.get(self.url, REMOTE_ADDR=EURO_IPV4)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_displayed(response)
        self._assert_continue_to_billing_displayed(response)
        self._assert_default_variation_selected_tax_19_eur(response)

    def test_get_displays_plan_selection_to_logged_in_us(self):
        user = create_customer_with_billing_address(
            vat_number='', country='US', region='NY', postal_code='12001'
        )
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self._assert_plan_selector_displayed(response)
        self._assert_continue_to_billing_displayed(response)
        self._assert_plan_selector_no_tax(response)

    def test_get_team_displays_plan_selection_to_logged_in_us(self):
        user = create_customer_with_billing_address(
            vat_number='', country='US', region='NY', postal_code='12001'
        )
        self.client.force_login(user)

        response = self.client.get(self.url_team)

        self.assertEqual(response.status_code, 200)
        self._assert_team_plan_selector_displayed(response)
        self._assert_continue_to_billing_displayed(response)
        self._assert_plan_selector_no_tax(response)

    # TODO(anna): tests for POST
