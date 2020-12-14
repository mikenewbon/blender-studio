from django.urls import path, include

from profiles.views.activity import Activity, Notifications
from profiles.views.api import NotificationMarkReadView, NotificationsMarkReadView
from profiles.views.webhooks import user_modified_webhook
import profiles.views.settings as settings

urlpatterns = [
    path('webhooks/user-modified', user_modified_webhook, name='webhook-user-modified'),
    path('notifications', Notifications.as_view(), name='profile-notifications'),
    path('activity', Activity.as_view(), name='profile-activity'),
    path(
        'settings/',
        include(
            [
                path('profile', settings.ProfileView.as_view(), name='profile-settings'),
                path('billing', settings.BillingView.as_view(), name='profile-settings-billing'),
                path('emails', settings.EmailsView.as_view(), name='profile-settings-emails'),
            ]
        ),
    ),
    path(
        'api/notifications/',
        include(
            [
                path(
                    '<int:pk>/mark-read',
                    NotificationMarkReadView.as_view(),
                    name='api-notification-mark-read',
                ),
                path(
                    'mark-read',
                    NotificationsMarkReadView.as_view(),
                    name='api-notifications-mark-read',
                ),
            ]
        ),
    ),
]
