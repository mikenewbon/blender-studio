"""Views handling subscription management."""
from typing import Optional
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import UpdateView, FormView
from waffle.mixins import WaffleFlagMixin

import looper.models
import looper.views.settings

from subscriptions.forms import BillingAddressForm, CancelSubscriptionForm, ChangePaymentMethodForm
from subscriptions.views.mixins import SingleSubscriptionMixin

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BillingAddressView(WaffleFlagMixin, LoginRequiredMixin, UpdateView):
    """Combine looper's Customer and Address into a billing address."""

    waffle_flag = "SUBSCRIPTIONS_ENABLED"

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


class CancelSubscriptionView(WaffleFlagMixin, SingleSubscriptionMixin, FormView):
    """Confirm and cancel a subscription."""

    waffle_flag = "SUBSCRIPTIONS_ENABLED"

    _log = logger

    template_name = 'subscriptions/cancel.html'
    form_class = CancelSubscriptionForm
    initial = {'confirm': False}

    def get_success_url(self) -> str:
        """Get a URL to redirect to upon success."""
        return reverse('user-settings-billing')

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


class PaymentMethodChangeView(WaffleFlagMixin, looper.views.settings.PaymentMethodChangeView):
    """Use the Braintree drop-in UI to switch a subscription's payment method."""

    waffle_flag = "SUBSCRIPTIONS_ENABLED"

    template_name = 'subscriptions/payment_method_change.html'
    form_class = ChangePaymentMethodForm
    success_url = '/settings/billing'

    subscription: looper.models.Subscription
