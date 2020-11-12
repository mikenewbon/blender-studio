from django.urls import path, include

from profiles.views.activity import activity, Notifications
from profiles.views.api import NotificationMarkReadView, NotificationsMarkReadView
from profiles.views.webhooks import user_modified_webhook

urlpatterns = [
    path('webhooks/user-modified', user_modified_webhook, name='webhook-user-modified'),
    path('notifications', Notifications.as_view(), name='profile-notifications'),
    path('activity', activity, name='profile-activity'),
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
