"""API for notification."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.http.response import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth import get_user_model

from users.models import Notification

User = get_user_model()


class NotificationMarkReadView(LoginRequiredMixin, SingleObjectMixin, View):
    """Allow users to mark specific notifications as read."""

    raise_exception = True
    model = Notification

    def post(self, request, *args, **kwargs):
        """Mark a notification as read."""
        notification = self.get_object()
        if notification.user != request.user:
            return HttpResponseForbidden()

        notification.date_read = timezone.now()
        notification.save(update_fields=['date_read'])

        return JsonResponse({})


class NotificationsMarkReadView(LoginRequiredMixin, View):
    """Allow users to mark all their unread notifications as read."""

    raise_exception = True
    model = Notification

    def post(self, request, *args, **kwargs):
        """Mark all previously unread notifications as read."""
        unread = self.model.objects.filter(user=request.user, date_read__isnull=True)
        now = timezone.now()
        for notification in unread:
            notification.date_read = now

        Notification.objects.bulk_update(unread, ['date_read'])

        return JsonResponse({})
