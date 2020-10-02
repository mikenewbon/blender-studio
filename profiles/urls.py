from django.urls import path

from profiles.views.webhooks import user_modified_webhook

urlpatterns = [
    path('api/webhooks/user-modified', user_modified_webhook, name='webhook-user-modified'),
]