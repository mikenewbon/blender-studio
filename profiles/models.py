from typing import Optional
import logging

from actstream.models import Action
from django import urls
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Case, When, Value, IntegerField
from django.urls import reverse

from common import mixins
from profiles.blender_id import BIDSession

bid = BIDSession()
logger = logging.getLogger(__name__)


class Profile(mixins.CreatedUpdatedMixin, models.Model):
    """Store additional Profile data, such as avatar and full name."""

    class Meta:
        permissions = [('can_view_content', 'Can view subscription-only content')]

    user = models.OneToOneField(
        User, primary_key=True, on_delete=models.CASCADE, related_name='profile'
    )
    full_name = models.CharField(max_length=255, blank=True, default='')
    is_subscribed_to_newsletter = models.BooleanField(default=False)

    def get_absolute_url(self):
        """Return absolute URL of a Profile."""
        return urls.reverse('profile_detail', kwargs={'pk': self.pk})

    def __str__(self) -> str:
        return f'Profile {self.user}'

    @property
    def image_url(self) -> Optional[str]:
        """Return a URL of the Profile image."""
        if not getattr(self.user, 'oauth_info', None) or not getattr(
            self.user.oauth_info, 'oauth_user_id'
        ):
            return None

        oauth_info = self.user.oauth_info
        return bid.get_avatar_url(oauth_info.oauth_user_id)

    @property
    def notifications(self):
        return (
            self.user.notifications.select_related('action').annotate(
                unread=Case(
                    When(date_read__isnull=True, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            # Unread notifications come first
            .order_by('unread', '-date_created')
        )

    @property
    def notifications_unread(self):
        return self.notifications.filter(date_read__isnull=True)


class Notification(models.Model):
    """Store additional data about an actstream notification.

    In general, it's not easy to determine if an action qualifies as a notification
    for a certain user because of the variaty of targets
    (assets, comments with relations to different pages and so on),
    so it's best to link actions to their relevant users when a new action is created.
    This simplifies retrieving notifications and checking if they can be marked as read.
    """

    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')

    date_created = models.DateTimeField(auto_now_add=True)
    date_read = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_created']

    @property
    def mark_read_url(self):
        """Return a URL that that allows marking this Notification as read."""
        return reverse('api-notification-mark-read', kwargs={'pk': self.pk})
