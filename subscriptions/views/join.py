"""Views handling subscription management."""
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import FormView

from looper.middleware import COUNTRY_CODE_SESSION_KEY
from looper.views.checkout import AbstractPaymentView, CheckoutView
import looper.gateways
import looper.middleware
import looper.models
import looper.money
import looper.taxes

from subscriptions.forms import BillingAddressForm, PaymentForm, AutomaticPaymentForm
from subscriptions.middleware import preferred_currency_for_country_code
from subscriptions.queries import should_redirect_to_billing
from subscriptions.signals import subscription_created_needs_payment
import subscriptions.models

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class _JoinMixin:
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

    def _get_existing_subscription(self):
        # Exclude cancelled subscriptions because they cannot transition to active
        existing_subscriptions = self.request.user.subscription_set.exclude(
            status__in=looper.models.Subscription._CANCELLED_STATUSES
        )
        return existing_subscriptions.first()

    def dispatch(self, request, *args, **kwargs):
        """Set customer for authenticated user, same as AbstractPaymentView does."""
        plan_variation_id = kwargs['plan_variation_id']
        self.plan_variation = get_object_or_404(
            looper.models.PlanVariation,
            pk=plan_variation_id,
            is_active=True,
            currency=self.get_currency(),
        )
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
        if should_redirect_to_billing(request.user):
            return redirect('user-settings-billing')

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Redirect anonymous users to login."""
        if request.user.is_anonymous:
            return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))

        if request.user.is_authenticated:
            if self.subscription and self.subscription.status in self.subscription._ACTIVE_STATUSES:
                return redirect('user-settings-billing')

        return super().post(request, *args, **kwargs)


class BillingDetailsView(_JoinMixin, LoginRequiredMixin, FormView):
    """Display billing details form and save them as billing Address and Customer."""

    template_name = 'subscriptions/join/billing_address.html'
    form_class = BillingAddressForm

    customer: looper.models.Customer

    def get_initial(self) -> dict:
        """Prefill default payment gateway, country and selected plan options."""
        initial = super().get_initial()
        # Only preset country when it's not already selected by the customer
        geoip_country = self.request.session.get(COUNTRY_CODE_SESSION_KEY)
        if geoip_country and (not self.customer or not self.customer.billing_address.country):
            initial['country'] = geoip_country

        # Only set initial values if they aren't already saved to the billing address.
        # Initial values always override form data, which leads to confusing issues with views.
        if not (self.customer and self.customer.billing_address.full_name):
            # Fall back to user's full name, if no full name set already in the billing address:
            if self.request.user.full_name:
                initial['full_name'] = self.request.user.full_name
        return initial

    def get_context_data(self, **kwargs) -> dict:
        """Add an extra form and gateway's client token."""
        return {
            **super().get_context_data(**kwargs),
            'current_plan_variation': self.plan_variation,
            'subscription': self.subscription,
        }

    def form_valid(self, form):
        """Save the billing details and pass the data to the payment form."""
        product_type = self.plan_variation.plan.product.type
        # Get the tax the same way the template does,
        # to detect if it was affected by changes to the billing details
        old_taxable = looper.taxes.Taxable.from_request(
            self.request, price=self.plan_variation.price, product_type=product_type
        )
        # Save the billing address
        # Because pre-filled country might be kept as is, has_changed() might not return True,
        # so we save the form unconditionally
        form.save()

        msg = 'Pricing has been updated to reflect changes to your billing details'
        new_country = self.customer.billing_address.country
        new_currency = preferred_currency_for_country_code(new_country)
        # Compare currency before and after the billing address is updated
        if self.plan_variation.currency != new_currency:
            # If currency has changed, find a matching plan variation for this new currency
            plan_variation = self.plan_variation.in_other_currency(new_currency)
            self.request.session[looper.middleware.PREFERRED_CURRENCY_SESSION_KEY] = new_currency
            messages.add_message(self.request, messages.INFO, msg)
            return redirect(
                'subscriptions:join-billing-details', plan_variation_id=plan_variation.pk
            )

        # Compare tax before and after the billing address is updated
        new_tax = self.customer.get_tax(product_type=product_type)
        new_taxable = looper.taxes.Taxable(self.plan_variation.price, *new_tax)
        if old_taxable != new_taxable:
            # If price has changed, stay on the same page and display a notification
            messages.add_message(self.request, messages.INFO, msg)
            return self.form_invalid(form)

        return redirect(
            'subscriptions:join-confirm-and-pay', plan_variation_id=self.plan_variation.pk
        )


class ConfirmAndPayView(_JoinMixin, LoginRequiredMixin, FormView):
    """Display the payment form and handle the payment flow."""

    raise_exception = True
    template_name = 'subscriptions/join/payment_method.html'
    form_class = PaymentForm

    log = logger
    gateway: looper.models.Gateway

    # FIXME(anna): this view uses some functionality of AbstractPaymentView/CheckoutView,
    # but cannot directly inherit from them.
    gateway_from_form = AbstractPaymentView.gateway_from_form

    _check_customer_ip_address = AbstractPaymentView._check_customer_ip_address
    _check_payment_method_nonce = CheckoutView._check_payment_method_nonce
    _check_recaptcha = CheckoutView._check_recaptcha

    _charge_if_supported = CheckoutView._charge_if_supported
    _fetch_or_create_order = CheckoutView._fetch_or_create_order

    def get_form_class(self):
        """Override the payment form based on the selected plan variation, before validation."""
        if self.plan_variation.collection_method == 'automatic':
            return AutomaticPaymentForm
        return PaymentForm

    def get_initial(self) -> dict:
        """Prefill default payment gateway, country and selected plan options."""
        product_type = self.plan_variation.plan.product.type
        customer_tax = self.customer.get_tax(product_type=product_type)
        taxable = looper.taxes.Taxable(self.plan_variation.price, *customer_tax)
        return {
            **super().get_initial(),
            'price': taxable.price.decimals_string,
            'gateway': self.gateway.name,
        }

    def get_context_data(self, **kwargs) -> dict:
        """Add an extra form and gateway's client token."""
        currency = self.get_currency()
        ctx = {
            **super().get_context_data(**kwargs),
            'current_plan_variation': self.plan_variation,
            'client_token': self.get_client_token(currency) if self.customer else None,
            'subscription': self.subscription,
        }
        return ctx

    def _get_or_create_subscription(
        self, gateway: looper.models.Gateway, payment_method: looper.models.PaymentMethod
    ) -> looper.models.Subscription:
        subscription = self._get_existing_subscription()
        is_new = False
        if not subscription:
            subscription = looper.models.Subscription()
            is_new = True
            self.log.debug('Creating an new subscription for %s, %s', gateway, payment_method)
        collection_method = self.plan_variation.collection_method
        supported = set(gateway.provider.supported_collection_methods)
        if collection_method not in supported:
            # FIXME(anna): this breaks plan selector because collection method
            # might not match the one selected by the customer.
            collection_method = supported.pop()

        with transaction.atomic():
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

            # Configure the team if this is a team plan
            if hasattr(subscription.plan, 'team_properties'):
                team_properties = subscription.plan.team_properties
                team, team_is_new = subscriptions.models.Team.objects.get_or_create(
                    subscription=subscription,
                    seats=team_properties.seats,
                )
                self.log.info(
                    '%s a team for subscription pk=%r, seats: %s',
                    team_is_new and 'Created' or 'Updated',
                    subscription.pk,
                    team.seats and team.seats or 'unlimited',
                )

        self.log.debug('%s subscription pk=%r', is_new and 'Created' or 'Updated', subscription.pk)
        return subscription

    def form_invalid(self, form):
        """Temporarily log all validation errors."""
        logger.exception('Validation error in ConfirmAndPayView: %s', form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        """Handle valid form data.

        Confirm and Pay view doesn't update the billing address,
        only displays it for use by payment flow and validates it on submit.
        The billing address is assumed to be saved at the previous step.
        """
        assert self.request.method == 'POST'

        response = self._check_recaptcha(form)
        if response:
            return response

        response = self._check_customer_ip_address(form)
        if response:
            return response

        gateway = self.gateway_from_form(form)
        payment_method = self._check_payment_method_nonce(form, gateway)
        if payment_method is None:
            return self.form_invalid(form)

        price_cents = int(Decimal(form.cleaned_data['price']) * 100)
        subscription = self._get_or_create_subscription(gateway, payment_method)
        # Update the tax info stored on the subscription
        subscription.update_tax()

        order = self._fetch_or_create_order(form, subscription)
        # Update the order to take into account latest changes
        order.update()
        # Make sure we are charging what we've displayed
        price = looper.money.Money(order.price.currency, price_cents)
        if order.price != price:
            form.add_error('', 'Payment failed: please reload the page and try again')
            return self.form_invalid(form)

        if not gateway.provider.supports_transactions:
            # Trigger an email with instructions about manual payment:
            subscription_created_needs_payment.send(sender=subscription)

        response = self._charge_if_supported(form, gateway, order)
        return response
