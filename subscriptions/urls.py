from django.urls import path, re_path
from django.views.generic import RedirectView

from looper.views import settings as looper_settings

from subscriptions.views.join import BillingDetailsView, ConfirmAndPayView
from subscriptions.views.select_plan_variation import (
    SelectPlanVariationView,
    SelectTeamPlanVariationView,
)
import subscriptions.views.settings as settings

# Required for URL namespace to work
app_name = 'subscriptions'

urlpatterns = [
    re_path(
        r'^join/(?:plan-variation/(?P<plan_variation_id>\d+)/)?$',
        SelectPlanVariationView.as_view(),
        name='join',
    ),
    re_path(
        r'^join/team/(?:plan-variation/(?P<plan_variation_id>\d+)/)?$',
        SelectTeamPlanVariationView.as_view(),
        name='join-team',
    ),
    path(
        'join/plan-variation/<int:plan_variation_id>/billing/',
        BillingDetailsView.as_view(),
        name='join-billing-details',
    ),
    path(
        'join/plan-variation/<int:plan_variation_id>/confirm/',
        ConfirmAndPayView.as_view(),
        name='join-confirm-and-pay',
    ),
    path(
        'subscription/<int:subscription_id>/manage/',
        settings.ManageSubscriptionView.as_view(),
        name='manage',
    ),
    path(
        'subscription/<int:subscription_id>/cancel/',
        settings.CancelSubscriptionView.as_view(),
        name='cancel',
    ),
    path(
        'subscription/<int:subscription_id>/payment-method/change/',
        settings.PaymentMethodChangeView.as_view(),
        name='payment-method-change',
    ),
    path(
        'subscription/order/<int:order_id>/pay/',
        settings.PayExistingOrderView.as_view(),
        name='pay-existing-order',
    ),
    path(
        'settings/billing-address/',
        settings.BillingAddressView.as_view(),
        name='billing-address',
    ),
    path('settings/receipts/', looper_settings.settings_receipts, name='receipts'),
    path(
        'settings/receipts/<int:order_id>',
        looper_settings.ReceiptView.as_view(),
        name='receipt',
    ),
    path(
        'settings/receipts/blender-studio-<int:order_id>.pdf',
        looper_settings.ReceiptPDFView.as_view(),
        name='receipt-pdf',
    ),
    # TODO(anna): remove this once blender-cloud-1243.pdf no longer appear in access logs.
    path(
        'settings/receipts/blender-cloud-<int:order_id>.pdf',
        RedirectView.as_view(pattern_name='subscriptions:receipt-pdf', permanent=True),
    ),
]
