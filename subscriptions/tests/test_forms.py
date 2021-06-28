import unittest

from subscriptions.forms import BillingAddressForm, PaymentForm
from subscriptions.tests.base import BaseSubscriptionTestCase

# maxDiff = None does not work for some obscure reason.
unittest.util._MAX_LENGTH = 1000
required_address_data = {
    'country': 'NL',
    'email': 'my.billing.email@example.com',
    'full_name': 'New Full Name',
    'locality': 'Amsterdam',
    'postal_code': '1000 AA',
    'street_address': 'MAIN ST 1',
}


class TestBillingAddressForm(BaseSubscriptionTestCase):
    def test_instance_loads_both_address_and_customer_data(self):
        form = BillingAddressForm(instance=self.billing_address)

        # N.B.: email is loaded from Customer.billing_email
        self.assertEqual(form['email'].value(), 'billing@example.com')
        self.assertEqual(form['company'].value(), 'Testcompany B.V.')
        self.assertEqual(form['country'].value(), 'NL')
        self.assertEqual(form['extended_address'].value(), 'Floor 1')
        self.assertEqual(form['full_name'].value(), 'Алексей Н.')
        self.assertEqual(form['locality'].value(), 'Amsterdam')
        self.assertEqual(form['postal_code'].value(), '1000AA')
        self.assertEqual(form['region'].value(), 'North Holland')
        self.assertEqual(form['street_address'].value(), 'Billing street 1')
        self.assertEqual(form['vat_number'].value(), 'NL-KVK-41202535')

    def test_validates_required_fields(self):
        form = BillingAddressForm(data={})

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'country': ['This field is required.'],
                'email': ['This field is required.'],
                'full_name': ['This field is required.'],
                'postal_code': ['This field is required.'],
            },
        )

    def test_validates_email_invalid(self):
        form = BillingAddressForm(
            instance=self.billing_address,
            data={
                **required_address_data,
                'email': 'obviouslynotanemail',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ['Enter a valid email address.']})

    def test_validates_postal_code_invalid_for_given_country_nl(self):
        form = BillingAddressForm(
            instance=self.billing_address,
            data={
                **required_address_data,
                'country': 'NL',
                'postal_code': '11111',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'postal_code': ['Enter a valid postal code in the format NNNN XX.']},
        )

    def test_validates_postal_code_invalid_for_given_country_gb(self):
        form = BillingAddressForm(
            instance=self.billing_address,
            data={
                **required_address_data,
                'country': 'GB',
                'postal_code': '11111',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            # cause generalising postal codes format for this wild country is an inhuman feat
            {'postal_code': ['Enter a valid postal code.']},
        )

    def test_validates_postal_code_invalid_for_given_country_us(self):
        form = BillingAddressForm(
            instance=self.billing_address,
            data={
                **required_address_data,
                'country': 'US',
                'region': 'NY',
                'postal_code': '111DSS',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'postal_code': ['Enter a valid ZIP code in the format XXXXX or XXXXX-XXXX.']},
        )

    def test_validates_vat_number_invalid_format(self):
        form = BillingAddressForm(
            data={
                **required_address_data,
                'vat_number': '!@#$!@#!#@$!',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'vat_number': ['!@#$!@#!#@$! is not a valid VAT identification number.']},
        )

    def test_validates_vat_number_invalid(self):
        form = BillingAddressForm(
            data={
                **required_address_data,
                'vat_number': 'NL12341234321',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'vat_number': ['NL12341234321 is not a valid VAT identification number.']},
        )

    def test_validates_vat_number_valid(self):
        form = BillingAddressForm(
            data={
                **required_address_data,
                'country': 'NL',
                'vat_number': 'NL818152011B01',
            }
        )

        self.assertTrue(form.is_valid())


class TestPaymentForm(BaseSubscriptionTestCase):
    required_payment_form_data = {
        'gateway': 'bank',
        'payment_method_nonce': 'fake-nonce',
        'plan_variation_id': 1,
        'price': '9.90',
    }

    def test_instance_loads_both_address_and_customer_data(self):
        form = PaymentForm(instance=self.billing_address)

        # N.B.: email is loaded from Customer.billing_email
        self.assertEqual(form['email'].value(), 'billing@example.com')
        self.assertEqual(form['company'].value(), 'Testcompany B.V.')
        self.assertEqual(form['country'].value(), 'NL')
        self.assertEqual(form['extended_address'].value(), 'Floor 1')
        self.assertEqual(form['full_name'].value(), 'Алексей Н.')
        self.assertEqual(form['locality'].value(), 'Amsterdam')
        self.assertEqual(form['postal_code'].value(), '1000AA')
        self.assertEqual(form['region'].value(), 'North Holland')
        self.assertEqual(form['street_address'].value(), 'Billing street 1')
        self.assertEqual(form['vat_number'].value(), 'NL-KVK-41202535')

    def test_validates_required_fields(self):
        form = PaymentForm(data={})

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'country': ['This field is required.'],
                'email': ['This field is required.'],
                'full_name': ['This field is required.'],
                'postal_code': ['This field is required.'],
                'gateway': ['This field is required.'],
                'payment_method_nonce': ['This field is required.'],
                'price': ['This field is required.'],
            },
        )

    def test_validates_email_invalid(self):
        form = PaymentForm(
            instance=self.billing_address,
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'email': 'obviouslynotanemail',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ['Enter a valid email address.']})

    def test_validates_postal_code_invalid_for_given_country_nl(self):
        form = PaymentForm(
            instance=self.billing_address,
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'country': 'NL',
                'postal_code': '11111',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'postal_code': ['Enter a valid postal code in the format NNNN XX.']},
        )

    def test_validates_postal_code_invalid_for_given_country_gb(self):
        form = PaymentForm(
            instance=self.billing_address,
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'country': 'GB',
                'postal_code': '11111',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            # cause generalising postal codes format for this wild country is an inhuman feat
            {'postal_code': ['Enter a valid postal code.']},
        )

    def test_validates_postal_code_invalid_for_given_country_us(self):
        form = PaymentForm(
            instance=self.billing_address,
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'country': 'US',
                'region': 'NY',
                'postal_code': '111DSS',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'postal_code': ['Enter a valid ZIP code in the format XXXXX or XXXXX-XXXX.']},
        )

    def test_validates_region_invalid_for_given_country_us(self):
        form = PaymentForm(
            instance=self.billing_address,
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'country': 'US',
                'region': 'AA',
                'postal_code': '11111',
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'region': ['Select a valid choice. AA is not one of the available choices.']},
        )

    def test_validates_vat_number_invalid_format(self):
        form = PaymentForm(
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'vat_number': '!@#$!@#!#@$!',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'vat_number': ['!@#$!@#!#@$! is not a valid VAT identification number.']},
        )

    def test_validates_vat_number_invalid(self):
        form = PaymentForm(
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'vat_number': 'NL12341234321',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'vat_number': ['NL12341234321 is not a valid VAT identification number.']},
        )

    def test_validates_vat_number_valid(self):
        form = PaymentForm(
            data={
                **self.required_payment_form_data,
                **required_address_data,
                'country': 'NL',
                'vat_number': 'NL818152011B01',
            }
        )

        self.assertTrue(form.is_valid())
