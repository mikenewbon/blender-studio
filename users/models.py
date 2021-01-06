from typing import Optional
import logging

from actstream.models import Action
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Case, When, Value, IntegerField
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_jsonfield_backport.models import JSONField

from common.upload_paths import get_upload_to_hashed_path

logger = logging.getLogger(__name__)


class User(AbstractUser):
    class Meta:
        db_table = 'auth_user'
        permissions = [('can_view_content', 'Can view subscription-only content')]

    email = models.EmailField(_('email address'), blank=False, null=False, unique=True)
    full_name = models.CharField(max_length=255, blank=True, default='')
    image = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True, null=True)
    is_subscribed_to_newsletter = models.BooleanField(default=False)
    badges = JSONField(null=True, blank=True)

    @property
    def image_url(self) -> Optional[str]:
        """Return a URL of the Profile image."""
        if not self.image:
            return static('common/images/blank-profile-pic.png')

        return self.image.url

    @property
    def notifications(self):
        return (
            self.notifications.select_related('action').annotate(
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
        db_table = 'users_notification'

    @property
    def mark_read_url(self):
        """Return a URL that that allows marking this Notification as read."""
        return reverse('api-notification-mark-read', kwargs={'pk': self.pk})
