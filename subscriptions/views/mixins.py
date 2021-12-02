"""Reusable mixins for views handling subscription management."""
from typing import Optional
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.utils import ErrorList
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from looper.models import Subscription

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BootstrapErrorList(ErrorList):
    """Render errors with Bootstrap classes."""

    def as_ul(self) -> str:
        """Render as ul."""
        if not self:
            return ''
        return '<ul class="errorlist alert alert-danger">{}</ul>'.format(
            ''.join([f'<li class="error">{e}</li>' for e in self])
        )


class SingleSubscriptionMixin(LoginRequiredMixin):
    """Get a single subscription of a logged in user."""

    @property
    def subscription_id(self) -> int:
        """Retrieve subscription ID."""
        return self.kwargs['subscription_id']

    def get_subscription(self) -> Subscription:
        """Retrieve Subscription object."""
        return get_object_or_404(self.request.user.subscription_set, pk=self.subscription_id)

    def get_context_data(self, **kwargs) -> dict:
        """Add Subscription to the template context."""
        subscription: Optional[Subscription] = self.get_subscription()
        return {
            **super().get_context_data(**kwargs),
            'subscription': subscription,
        }

    def dispatch(self, request, *args, **kwargs):
        """Allow the view to do things that rely on auth state before dispatch.

        The AnonymousUser instance doesn't have a 'subscriptions' property,
        but login checking only happens in the super().dispatch() call.
        """
        if not hasattr(request.user, 'subscription_set'):
            return self.handle_no_permission()
        response = self.pre_dispatch(request, *args, **kwargs)
        if response:
            return response
        return super().dispatch(request, *args, **kwargs)

    def pre_dispatch(self, request, *args, **kwargs) -> Optional[HttpResponse]:
        """Called between a permission check and calling super().dispatch().

        This allows you to get the current subscription, or otherwise do things
        that require the user to be logged in.

        :return: None to continue handling this request, or a
            HttpResponse to stop processing early.
        """


class BootstrapErrorListMixin:
    """Override get_form method changing error_class of the form."""

    def get_form(self, *args, **kwargs):
        """Override form error list class with a Bootstrap-compatible one."""
        form = super().get_form(*args, **kwargs)
        form.error_class = BootstrapErrorList
        return form
