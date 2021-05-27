"""Override some of looper model forms."""
from typing import List, Tuple

from django import forms
from django.core.exceptions import ValidationError
from django.forms.fields import Field
from django.forms.models import model_to_dict

from localflavor.administrative_areas import ADMINISTRATIVE_AREAS
from localflavor.generic.validators import validate_country_postcode
from stdnum.eu import vat
import localflavor.exceptions

import looper.form_fields
import looper.forms
import looper.models

from subscriptions.form_fields import RegionSelect
from subscriptions.validators import VATINValidator

BILLING_DETAILS_PLACEHOLDERS = {
    'full_name': 'Your Full Name',
    'street_address': 'Street address',
    'postal_code': 'ZIP/Postal code',
    'region': 'State or province, if applicable',
    'company': 'Company, if applicable',
    'extended_address': 'Extended address, if applicable',
    'locality': 'City',
    'country': 'Country',
    'email': 'mail@example.com',
    'vat_number': 'VAT identification number',
}
LABELS = {
    'vat_number': 'VAT Number',
    'company': 'Company',
    'extended_address': 'Extended address',
}
REQUIRED_FIELDS = {
    'country',
    'email',
    'full_name',
    'locality',
    'postal_code',
    'street_address',
}


class BillingAddressForm(forms.ModelForm):
    """Unify Customer and Address in a single form."""

    # Customer.billing_email is exposed as email in the Form
    # because Looper scripts and forms already use "email" everywhere.
    __customer_fields = {'billing_email': 'email', 'vat_number': 'vat_number'}
    # Colliding "full_name" and "company" values are taken from and saved to the Address.
    # FIXME(anna): do we need to use company and full_name on the Customer or only Address?

    class Meta:
        model = looper.models.Address
        fields = looper.models.Address.PUBLIC_FIELDS

    # What kind of choices are allowed depends on the selected country
    # and is not yet known when the form is rendered.
    region = forms.ChoiceField(required=False, widget=RegionSelect)
    vat_number = forms.CharField(required=False, validators=[VATINValidator()])
    email = forms.EmailField(required=True)

    def _get_region_choices_and_label(self, country_code: str) -> List[Tuple[str, str]]:
        regions = ADMINISTRATIVE_AREAS.get(country_code)
        if regions:
            is_required = regions.get('used_in_address', False)
            if is_required:
                return regions['choices'], regions['type'].capitalize()
        return [], ''

    def __init__(self, *args, **kwargs):
        """Load additional model data from Customer and set form placeholders."""
        instance: looper.models.Address = kwargs.get('instance')
        if instance:
            assert isinstance(instance, looper.models.Address), 'Must be an instance of Address'
            customer = instance.user.customer
            initial = kwargs.get('initial') or {}
            customer_data = model_to_dict(customer, self.__customer_fields.keys(), {})
            # Remap the fields, e.g. turning "billing_email" into "email"
            customer_form_data = {v: customer_data[k] for k, v in self.__customer_fields.items()}
            # Add Customer data into initial,
            # making sure that it still overrides the instance data, as it's supposed to
            kwargs['initial'] = {
                **customer_form_data,
                **initial,
            }
            if not kwargs['initial'].get('full_name'):
                kwargs['initial']['full_name'] = instance.user.full_name

        super().__init__(*args, **kwargs)

        # Set placeholder values on all form fields
        for field_name, field in self.fields.items():
            placeholder = BILLING_DETAILS_PLACEHOLDERS.get(field_name)
            if placeholder:
                field.widget.attrs['placeholder'] = placeholder
            label = LABELS.get(field_name)
            if label:
                field.label = label
            # Require the required fields
            if field_name in REQUIRED_FIELDS:
                field.required = True

        # Set region choices, in case country is selected or loaded from the instance
        country_code = self.data.get('country') or self.initial.get('country')
        region_field = self.fields['region']
        choices, label = self._get_region_choices_and_label(country_code)
        region_field.choices = choices
        region_field.label = label
        region_field.required = True if region_field.choices else False

    def clean(self):
        """Perform additional validation of the billing address."""
        cleaned_data = super().clean()

        self.clean_postal_code_and_country(cleaned_data)
        self.clean_vat_number_and_country(cleaned_data)

        return cleaned_data

    def clean_postal_code_and_country(self, cleaned_data):
        """Validate the country and postal codes together."""
        country_code = cleaned_data.get('country')
        postal_code = cleaned_data.get('postal_code')
        if postal_code:
            if not country_code:
                self.add_error(
                    'country',
                    ValidationError(Field.default_error_messages['required'], 'required'),
                )
            try:
                cleaned_data['postal_code'] = validate_country_postcode(postal_code, country_code)
            except localflavor.exceptions.ValidationError as e:
                self.add_error(
                    'postal_code',
                    ValidationError(str(e), 'invalid'),
                )

    def clean_vat_number_and_country(self, cleaned_data):
        """Validate the VATIN and country code together."""
        country_code = cleaned_data.get('country')
        vat_number = cleaned_data.get('vat_number')
        # TODO(anna): we could prefill the company address based VATIN data here.
        if vat_number:
            vat_number_country_code = next(iter(vat.guess_country(vat_number)), '').upper()
            if vat_number_country_code != country_code:
                self.add_error(
                    'vat_number',
                    ValidationError(
                        'Billing address country must match country of VATIN',
                        'invalid',
                    ),
                )

    def save(self, commit=True):
        """Save Customer data as well."""
        # Validation against region choices is already done, because choices are set on __init__,
        # however Django won't set the updated blank region value if was omitted from the form.
        if self.cleaned_data['region'] == '':
            self.instance.region = ''
        instance = super().save(commit=commit)

        customer = instance.user.customer
        for model_field, form_field in self.__customer_fields.items():
            setattr(customer, model_field, self.cleaned_data[form_field])
        if commit:
            customer.save(update_fields=self.__customer_fields)
        return instance


class BillingAddressReadonlyForm(BillingAddressForm):
    """Readonly version of the above form, for use on the "Confirm and Pay" step of the checkout."""

    def __init__(self, *args, **kwargs):
        """Add a "readonly" attribute all fields."""
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Only make billing details fields readonly (this form is inherited by other forms)
            if field_name not in BILLING_DETAILS_PLACEHOLDERS:
                continue
            field.widget.attrs['readonly'] = True
            if field.widget.input_type == 'select':
                continue
            # Try to adjust inputs width to their current values for compact display
            value = self.data.get(field_name, self.initial.get(field_name, ''))
            field.widget.attrs['size'] = len(str(value))


class BillingAddressHiddenForm(BillingAddressForm):
    """Hidden version of the billing address form, for use in "Change Payment"."""

    def __init__(self, *args, **kwargs):
        """Add a "hidden" attribute all fields."""
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Only make billing details fields hidden (this form is inherited by other forms)
            if field_name not in BILLING_DETAILS_PLACEHOLDERS:
                continue
            field.widget.attrs['hidden'] = True


class BillingDetailsForm(BillingAddressForm):
    """Handle full billing details and PlanVariation ID in the first step of the checkout.

    Selected plan options carry over to the next step of the checkout.
    """

    plan_variation_id = forms.IntegerField(required=True)


class PaymentForm(BillingAddressReadonlyForm):
    """Handle PlanVariation ID and payment method details in the second step of the checkout.

    Billing details are displayed as read-only and cannot be edited,
    but are still used by the payment flow.
    """

    payment_method_nonce = forms.CharField(initial='set-in-javascript', widget=forms.HiddenInput())
    gateway = looper.form_fields.GatewayChoiceField()
    device_data = forms.CharField(
        initial='set-in-javascript', widget=forms.HiddenInput(), required=False
    )

    price = forms.CharField(widget=forms.HiddenInput(), required=True)
    plan_variation_id = forms.IntegerField(required=True)

    # These are used when a payment fails, so that the next attempt to pay can reuse
    # the already-created subscription and order.
    subscription_pk = forms.CharField(widget=forms.HiddenInput(), required=False)
    order_pk = forms.CharField(widget=forms.HiddenInput(), required=False)


class AutomaticPaymentForm(PaymentForm):
    """Same as the PaymentForm, but only allows payment gateways that support transactions."""

    gateway = looper.form_fields.GatewayChoiceField(
        queryset=looper.models.Gateway.objects.filter(
            name__in=looper.gateways.Registry.gateway_names_supports_transactions()
        )
    )


class ChangePaymentMethodForm(BillingAddressHiddenForm, looper.forms.ChangePaymentMethodForm):
    """Add full billing address to the change payment form."""

    pass


class CancelSubscriptionForm(forms.Form):
    """Confirm cancellation of a subscription."""

    confirm = forms.BooleanField(label='Confirm Subscription Cancellation')


class PayExistingOrderForm(AutomaticPaymentForm):
    """Form for paying for an outstanding order."""

    def __init__(self, *args, **kwargs):
        """Work around Django's `exclude` bug by removing unused fields manually.

        See https://code.djangoproject.com/ticket/8620
        """
        super().__init__(*args, **kwargs)
        self.fields.pop('plan_variation_id')