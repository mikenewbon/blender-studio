"""Views handling plan selection widget."""
from typing import Optional
import logging

from django.shortcuts import redirect
from django.views.generic import FormView

from looper.views.checkout import AbstractPaymentView
import looper.gateways
import looper.middleware
import looper.models
import looper.money
import looper.taxes

from subscriptions.forms import SelectPlanVariationForm
from subscriptions.queries import should_redirect_to_billing

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class _PlanSelectorMixin:
    get_currency = AbstractPaymentView.get_currency
    select_team_plans = False

    def _get_plans(self):
        return looper.models.Plan.objects.filter(
            is_active=True,
            team_properties__isnull=not self.select_team_plans,
        )

    def _get_default_plan_variation(self):
        return self._get_plans().first().variation_for_currency(self.get_currency())

    def _get_plan_variation(self, plan_variation_id) -> Optional[looper.models.PlanVariation]:
        if not plan_variation_id:
            return None
        try:
            return looper.models.PlanVariation.objects.active().get(
                pk=plan_variation_id,
                currency=self.get_currency(),
                plan__team_properties__isnull=not self.select_team_plans,
            )
        except looper.models.PlanVariation.DoesNotExist:
            return None


class SelectPlanVariationView(_PlanSelectorMixin, FormView):
    """Display available subscription plans."""

    template_name = 'subscriptions/join/select_plan_variation.html'
    form_class = SelectPlanVariationForm
    select_team_plans = False

    def get(self, request, *args, **kwargs):
        """Get optional plan_variation_id from the URL and set it on the view.

        Also check the feature flag and redirect to Blender Store if not active.
        """
        if should_redirect_to_billing(request.user):
            return redirect('user-settings-billing')

        plan_variation_id = kwargs.get('plan_variation_id')
        plan_variation = self._get_plan_variation(plan_variation_id)
        if not plan_variation:
            plan_variation = self._get_default_plan_variation()
        self.plan_variation = plan_variation
        self.plan = plan_variation.plan
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict:
        """Add an extra form and gateway's client token."""
        ctx = {
            **super().get_context_data(**kwargs),
            'plans': self._get_plans(),
            'current_plan_variation': self.plan_variation,
            'select_team_plans': self.select_team_plans,
        }
        return ctx

    def get_initial(self) -> dict:
        """Add currency to the form initial parameters: it's used in form validation."""
        return {
            **super().get_initial(),
            'currency': self.get_currency(),
        }

    def form_valid(self, form):
        """Save the billing details and pass the data to the payment form."""
        plan_variation_id = form.cleaned_data['plan_variation_id']
        return redirect('subscriptions:join-billing-details', plan_variation_id=plan_variation_id)


class SelectTeamPlanVariationView(SelectPlanVariationView):
    """Display available team subscription plans."""

    select_team_plans = True
