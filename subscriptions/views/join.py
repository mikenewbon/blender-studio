"""Views handling subscription management."""
from decimal import Decimal
from typing import Optional
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views.generic import FormView
import waffle

from looper.middleware import COUNTRY_CODE_SESSION_KEY
from looper.utils import clean_ip_address
from looper.views.checkout import AbstractPaymentView, CheckoutView
import looper.gateways
import looper.models
import looper.money
import looper.taxes

from subscriptions.forms import BillingDetailsForm, PaymentForm, AutomaticPaymentForm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class _JoinMixin:
    gateway: looper.models.Gateway
    customer: looper.models.Customer

    # FIXME(anna): this view uses some functionality of AbstractPaymentView,
    # but cannot directly inherit from them, since JoinView supports creating only one subscription.
    get_currency = AbstractPaymentView.get_currency
    get_client_token = AbstractPaymentView.get_client_token
    client_token_session_key = AbstractPaymentView.client_token_session_key
    erase_client_token = AbstractPaymentView.erase_client_token

    @property
    def session_key_prefix(self) -> str:
        """Separate client tokens by currency code."""
        currency = self.get_currency()
        return f'PAYMENT_GATEWAY_CLIENT_TOKEN_{currency}'

    def _get_payment_form_class_with_restricted_gateways(self):
        if self.plan_variation.collection_method == 'automatic':
            return AutomaticPaymentForm
        return PaymentForm

    def _get_plans(self):
        return looper.models.Plan.objects.filter(is_active=True)

    def _get_existing_subscription(self):
        existing_subscriptions = self.request.user.subscription_set
        existing_count = existing_subscriptions.count()
        assert existing_count < 2, f'More than one subscription exists: {existing_count}'
        return self.request.user.subscription_set.first()

    def _get_default_plan_variation(self):
        return self._get_plans().first().variation_for_currency(self.get_currency())

    def get_initial(self) -> dict:
        """Prefill default payment gateway, country and selected plan options."""
        initial = {
            'gateway': self.gateway.name,
        }
        # Only preset country when it's not already selected by the customer
        geoip_country = self.request.session.get(COUNTRY_CODE_SESSION_KEY)
        logger.warning('IP "%s", geoip_country "%s"', clean_ip_address(self.request), geoip_country)
        if geoip_country and (not self.customer or not self.customer.billing_address.country):
            initial['country'] = geoip_country
        plan_variation_id = self.request.session.get('plan_variation_id', None)
        plan_variation = self._get_plan_variation(plan_variation_id)
        if not plan_variation:
            plan_variation = self._get_default_plan_variation()
        initial['plan_variation_id'] = plan_variation.id
        return initial

    def _get_plan_variation(self, plan_variation_id) -> Optional[looper.models.PlanVariation]:
        if not plan_variation_id:
            return None
        try:
            return looper.models.PlanVariation.objects.active().get(
                pk=plan_variation_id, currency=self.get_currency()
            )
        except looper.models.PlanVariation.DoesNotExist:
            return None

    def _check_plan_variation(self, form):
        # Clear the previously saved selection
        self.request.session.pop('plan_variation_id', None)

        # Get the selected plan variation
        plan_variation_id = form.cleaned_data['plan_variation_id']
        self.plan_variation = self._get_plan_variation(plan_variation_id)
        if not self.plan_variation:
            form.add_error('', 'Unexpected error: please reload the page and try again')
            return self.form_invalid(form)

        self.request.session['plan_variation_id'] = self.plan_variation.id

    def dispatch(self, request, *args, **kwargs):
        """Set customer for authenticated user, same as AbstractPaymentView does."""
        if not getattr(self, 'gateway', None):
            self.gateway = looper.models.Gateway.default()
        self.user = self.request.user
        self.customer = None
        self.subscription = None
        if self.user.is_authenticated:
            self.customer = self.user.customer
            self.subscription = self._get_existing_subscription()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        """Pass extra parameters to the form."""
        form_kwargs = super().get_form_kwargs()
        if self.user.is_authenticated:
            return {
                **form_kwargs,
                'instance': self.customer.billing_address,
            }
        return form_kwargs

    def get(self, request, *args, **kwargs):
        """Redirect to the Store if subscriptions are not enabled."""
        if not waffle.flag_is_active(request, 'SUBSCRIPTIONS_ENABLED'):
            return redirect(settings.STORE_PRODUCT_URL)

        if request.user.is_authenticated:
            if self.subscription and self.subscription.status in self.subscription._ACTIVE_STATUSES:
                return redirect('user-settings-billing')

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Redirect anonymous users to login."""
        if not waffle.flag_is_active(request, 'SUBSCRIPTIONS_ENABLED'):
            return redirect(settings.STORE_PRODUCT_URL)

        if request.user.is_anonymous:
            return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))

        if request.user.is_authenticated:
            if self.subscription and self.subscription.status in self.subscription._ACTIVE_STATUSES:
                return redirect('user-settings-billing')

        return super().post(request, *args, **kwargs)


class JoinView(_JoinMixin, FormView):
    """Display subscription plans and handle creating a new subscription.

    Shows a plan selector to anonymous viewers and a step 1 of the checkout to logged in ones.
    """

    template_name = 'subscriptions/join/billing_address.html'
    template_name_anonymous = 'subscriptions/join/anonymous.html'
    form_class = BillingDetailsForm

    gateway: looper.models.Gateway
    customer: looper.models.Customer

    @property
    def form_class_payment(self):
        """Return next step form depending on currently selected plan variation."""
        return self._get_payment_form_class_with_restricted_gateways()

    def get_template_names(self):
        """Return a different template for anonymous viewers."""
        if self.request.user.is_anonymous:
            return [self.template_name_anonymous]
        return [self.template_name]

    def get_context_data(self, **kwargs) -> dict:
        """Add an extra form and gateway's client token."""
        ctx = {
            **super().get_context_data(**kwargs),
            'plans': self._get_plans(),
            'subscription': self.subscription,
        }
        return ctx

    def form_valid(self, form):
        """Save the billing details and pass the data to the payment form."""
        response = self._check_plan_variation(form)
        if response:
            return response

        product_type = self.plan_variation.plan.product.type
        old_tax = self.customer.get_tax(product_type=product_type)
        # Save the billing address
        if form.has_changed():
            form.save()

        # Compare tax before and after the billing address is updated
        new_tax = self.customer.get_tax(product_type=product_type)
        old_taxable = looper.taxes.Taxable(self.plan_variation.price, *old_tax)
        new_taxable = looper.taxes.Taxable(self.plan_variation.price, *new_tax)
        if old_taxable != new_taxable:
            # If price has changed, stay on the same page and display a notification
            messages.add_message(
                self.request,
                messages.INFO,
                'Pricing has been updated to reflect changes to your billing details',
            )
            return self.form_invalid(form)

        # Use the same data to initialize the form for the next step of the checkout
        next_form_kwargs = self.get_form_kwargs()
        next_form = self.form_class_payment(
            # Billing address data must be loaded from the self.customer instance,
            # which has already been saved:
            instance=next_form_kwargs['instance'],
            initial={
                # Initial values are only displayed for unbound forms, but we need the
                # because they contain the default gateway:
                **next_form_kwargs['initial'],
                # We also need to pass over plan selection
                **form.cleaned_data,
                # Set the final price that will also be the price of the order
                'price': new_taxable.price.decimals_string,
            },
        )
        currency = self.get_currency()
        ctx = {
            **self.get_context_data(),
            'client_token': self.get_client_token(currency),
            'form': next_form,
        }
        return render(self.request, JoinConfirmView.template_name, context=ctx)


class JoinConfirmView(_JoinMixin, LoginRequiredMixin, FormView):
    """Select your payment method: step 2 of the new subscription flow."""

    raise_exception = True
    template_name = 'subscriptions/join/payment_method.html'
    form_class = PaymentForm

    log = logger

    def get_context_data(self, **kwargs) -> dict:
        """Add an extra form and gateway's client token."""
        currency = self.get_currency()
        ctx = {
            **super().get_context_data(**kwargs),
            'plans': self._get_plans(),
            'client_token': self.get_client_token(currency) if self.customer else None,
            'subscription': self.subscription,
        }
        return ctx

    def get_form(self, form_class=None):
        """Override the payment form based on the selected plan variation, before validation."""
        form_kwargs = self.get_form_kwargs()
        form_class = self.get_form_class()
        # Cannot yet retrieve plan_variation_id from the cleaned data
        plan_variation_id = form_kwargs.get('data', {}).get('plan_variation_id')
        if plan_variation_id:
            self.plan_variation = self._get_plan_variation(plan_variation_id)
            form_class = self._get_payment_form_class_with_restricted_gateways()
        return form_class(**form_kwargs)

    # FIXME(anna): this view uses some functionality of AbstractPaymentView/CheckoutView,
    # but cannot directly inherit from them.
    gateway_from_form = AbstractPaymentView.gateway_from_form

    _check_customer_ip_address = AbstractPaymentView._check_customer_ip_address
    _check_payment_method_nonce = CheckoutView._check_payment_method_nonce
    _check_recaptcha = CheckoutView._check_recaptcha

    _charge_if_supported = CheckoutView._charge_if_supported
    _fetch_or_create_order = CheckoutView._fetch_or_create_order

    def _get_or_create_subscription(
        self, gateway: looper.models.Gateway, payment_method: looper.models.PaymentMethod
    ) -> looper.models.Subscription:
        subscription = self._get_existing_subscription()
        if not subscription:
            subscription = looper.models.Subscription()
            self.log.debug('Creating an new subscription for %s, %s', gateway, payment_method)
        collection_method = self.plan_variation.collection_method
        supported = set(gateway.provider.supported_collection_methods)
        # FIXME(anna): looper only allows automatic collection with BraintreeGateway,
        # which is what was required for DevFund, but we need to maintain what is
        # possible with Cloud subscriptions in the Store,
        # which allows manual plans with Braintree payment methods:
        if isinstance(gateway.provider, looper.gateways.BraintreeGateway):
            supported.add('manual')
        if collection_method not in supported:
            # FIXME(anna): this breaks plan selector because collection method
            # might not match the one selected by the customer.
            collection_method = supported.pop()

        subscription.plan = self.plan_variation.plan
        subscription.user = self.user
        subscription.payment_method = payment_method
        # Currency must be set before the price, in case it was changed
        subscription.currency = self.plan_variation.currency
        subscription.price = self.plan_variation.price
        subscription.interval_unit = self.plan_variation.interval_unit
        subscription.interval_length = self.plan_variation.interval_length
        subscription.collection_method = collection_method
        subscription.save()

        self.log.debug('Updated subscription pk=%r', subscription.pk)
        return subscription

    def form_valid(self, form):
        """Handle valid form data."""
        assert self.request.method == 'POST'

        response = self._check_recaptcha(form)
        if response:
            return response

        response = self._check_customer_ip_address(form)
        if response:
            return response

        # Validate and store selected plan options in the session,
        # in case they go back to billing details step
        response = self._check_plan_variation(form)
        if response:
            return response

        gateway = self.gateway_from_form(form)
        payment_method = self._check_payment_method_nonce(form, gateway)
        if payment_method is None:
            return self.form_invalid(form)

        subscription = self._get_or_create_subscription(gateway, payment_method)
        # Update the tax info stored on the subscription
        subscription.update_tax()

        order = self._fetch_or_create_order(form, subscription)
        # Update the order to take into account latest changes
        order.update()
        # Make sure we are charging what we've displayed
        price_cents = int(Decimal(form.cleaned_data['price']) * 100)
        price = looper.money.Money(order.price.currency, price_cents)
        if order.price != price:
            form.add_error('', 'Payment failed: please reload the page and try again')
            return self.form_invalid(form)

        response = self._charge_if_supported(form, gateway, order)
        return response
