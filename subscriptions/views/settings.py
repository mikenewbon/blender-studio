"""Views handling subscription management."""
from typing import Optional
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import UpdateView, FormView

import looper.models
import looper.views.settings

from subscriptions.forms import (
    BillingAddressForm,
    CancelSubscriptionForm,
    ChangePaymentMethodForm,
    PayExistingOrderForm,
    TeamForm,
)
from subscriptions.views.mixins import SingleSubscriptionMixin, BootstrapErrorListMixin
import subscriptions.models

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BillingAddressView(LoginRequiredMixin, UpdateView):
    """Combine looper's Customer and Address into a billing address."""

    template_name = 'settings/billing_address.html'
    model = looper.models.Address
    form_class = BillingAddressForm
    success_url = reverse_lazy('subscriptions:billing-address')

    def _get_customer_object(self) -> Optional[looper.models.Customer]:
        if self.request.user.is_anonymous:
            return None
        return self.request.user.customer

    def get_object(self, queryset=None) -> Optional[looper.models.Address]:
        """Get billing address."""
        customer = self._get_customer_object()
        return customer.billing_address if customer else None


class CancelSubscriptionView(SingleSubscriptionMixin, FormView):
    """Confirm and cancel a subscription."""

    _log = logger

    template_name = 'subscriptions/cancel.html'
    form_class = CancelSubscriptionForm
    initial = {'confirm': False}
    success_url = reverse_lazy('user-settings-billing')

    def form_valid(self, form):
        """Cancel the subscription."""
        subscription = self.get_subscription()
        self._log.info(
            'Cancelling subscription pk=%d on behalf of user pk=%d',
            subscription.pk,
            self.request.user.pk,
        )
        subscription.cancel_subscription()
        return super().form_valid(form)


class PaymentMethodChangeView(looper.views.settings.PaymentMethodChangeView):
    """Use the Braintree drop-in UI to switch a subscription's payment method."""

    template_name = 'subscriptions/payment_method_change.html'
    form_class = ChangePaymentMethodForm
    success_url = reverse_lazy('user-settings-billing')

    subscription: looper.models.Subscription

    def get_initial(self) -> dict:
        """Modify initial form data."""
        initial = super().get_initial()
        initial['next_url_after_done'] = self.success_url

        # Looper's view uses customer full_name, we don't
        initial.pop('full_name', None)

        # Only set initial values if they aren't already saved to the billing address.
        # Initial values always override form data, which leads to confusing issues with views.
        if not (self.customer and self.customer.billing_address.full_name):
            # Fall back to user's full name, if no full name set already in the billing address:
            if self.request.user.full_name:
                initial['full_name'] = self.request.user.full_name
        return initial

    def form_invalid(self, form):
        """Temporarily log all validation errors."""
        logger.exception('Validation error in ChangePaymentMethodForm: %s', form.errors)
        return super().form_invalid(form)


class PayExistingOrderView(looper.views.checkout.CheckoutExistingOrderView):
    """Override looper's view with our forms."""

    # Redirect to LOGIN_URL instead of raising an exception
    raise_exception = False
    template_name = 'subscriptions/pay_existing_order.html'
    form_class = PayExistingOrderForm
    success_url = reverse_lazy('user-settings-billing')

    def get_initial(self) -> dict:
        """Prefill the payment amount and missing form data, if any."""
        initial = {
            'price': self.order.price.decimals_string,
            'email': self.customer.billing_email,
        }

        # Only set initial values if they aren't already saved to the billing address.
        # Initial values always override form data, which leads to confusing issues with views.
        if not (self.customer and self.customer.billing_address.full_name):
            # Fall back to user's full name, if no full name set already in the billing address:
            if self.request.user.full_name:
                initial['full_name'] = self.request.user.full_name
        return initial

    def form_invalid(self, form):
        """Temporarily log all validation errors."""
        logger.exception('Validation error in PayExistingOrderView: %s', form.errors)
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        """Return 403 unless current session and the order belong to the same user.

        Looper renders a template instead, we just want to display the standard 403 page
        or redirect to login, like LoginRequiredMixin does with raise_exception=False.
        """
        self.order = get_object_or_404(looper.models.Order, pk=kwargs['order_id'])
        if request.user.is_authenticated and self.order.user_id != request.user.id:
            return HttpResponseForbidden()
        self.plan = self.order.subscription.plan
        return super(looper.views.checkout.CheckoutExistingOrderView, self).dispatch(
            request, *args, **kwargs
        )


class ManageSubscriptionView(
    SuccessMessageMixin, SingleSubscriptionMixin, BootstrapErrorListMixin, UpdateView
):
    """View and manage a subscription."""

    template_name = 'subscriptions/manage.html'
    form_class = TeamForm
    model = subscriptions.models.Team
    pk_url_kwarg = 'subscription_id'
    success_message = 'Team subscription updated successfully'

    def get_object(self, queryset=None):
        """Get team if this is a team subscription."""
        subscription = self.get_subscription()
        return subscription.team if hasattr(subscription, 'team') else None

    def get_success_url(self):
        """Display the same manage subscription page when done editing the team."""
        return reverse(
            'subscriptions:manage', kwargs={'subscription_id': self.object.subscription_id}
        )
