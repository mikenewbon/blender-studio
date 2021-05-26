from django.urls import path

from looper.views import settings as looper_settings

import subscriptions.views.join as join
import subscriptions.views.settings as settings

# Required for URL namespace to work
app_name = 'subscriptions'

urlpatterns = [
    path('join/', join.JoinView.as_view(), name='join'),
    path('join/confirm/', join.JoinConfirmView.as_view(), name='join-confirm-and-pay'),
    path(
        'subscription/<int:subscription_id>/cancel',
        settings.CancelSubscriptionView.as_view(),
        name='cancel',
    ),
    path(
        'subscription/<int:subscription_id>/payment-method/change',
        settings.PaymentMethodChangeView.as_view(),
        name='payment-method-change',
    ),
    path(
        'subscription/order/<int:order_id>/pay',
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
        'settings/receipts/blender-cloud-<int:order_id>.pdf',
        looper_settings.ReceiptPDFView.as_view(),
        name='receipt-pdf',
    ),
]
