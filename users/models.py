from typing import Optional
import logging
import time

from actstream.models import Action
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.models import AbstractUser
from django.db import models, DEFAULT_DB_ALIAS, transaction
from django.db.models import Case, When, Value, IntegerField
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_jsonfield_backport.models import JSONField

from common.upload_paths import get_upload_to_hashed_path

logger = logging.getLogger(__name__)


def shortuid() -> str:
    """Generate a 14-characters long string ID based on time."""
    return hex(int(time.monotonic() * 10 ** 10))[2:]


class User(AbstractUser):
    class Meta:
        db_table = 'auth_user'
        permissions = [('can_view_content', 'Can view subscription-only content')]

    email = models.EmailField(_('email address'), blank=False, null=False, unique=True)
    full_name = models.CharField(max_length=255, blank=True, default='')
    image = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True, null=True)
    is_subscribed_to_newsletter = models.BooleanField(default=False)
    badges = JSONField(null=True, blank=True)

    date_deletion_requested = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.full_name or self.username} ({self.email})'

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

    def _get_nested_objects_collector(self) -> NestedObjects:
        collector = NestedObjects(using=DEFAULT_DB_ALIAS)
        collector.collect([self])
        return collector

    @property
    def can_be_deleted(self) -> bool:
        """Fetch objects referencing this profile and determine if it can be deleted."""
        if self.is_staff or self.is_superuser:
            return False
        collector = self._get_nested_objects_collector()
        if collector.protected:
            return False
        return True

    def request_deletion(self, date_deletion_requested):
        """Store date of the deletion request and deactivate the user."""
        if not self.can_be_deleted:
            logger.error('Deletion requested for a protected account pk=%s, ignoring', self.pk)
            return
        logger.warning(
            'Deletion of pk=%s requested on %s, deactivating this account',
            self.pk,
            date_deletion_requested,
        )
        self.is_active = False
        self.date_deletion_requested = date_deletion_requested
        self.is_subscribed_to_newsletter = False
        self.save(
            update_fields=['is_active', 'date_deletion_requested', 'is_subscribed_to_newsletter']
        )

    @transaction.atomic
    def anonymize_or_delete(self):
        """Delete user completely if they don't have a subscription with order, otherwise anonymize.

        Does nothing if deletion hasn't been explicitly requested earlier.
        """
        import looper.admin_log as admin_log
        import looper.models
        import subscriptions.queries

        if not self.can_be_deleted:
            looper.error(
                'User.anonymize called, but pk=%s cannot be deleted',
                self.pk,
            )
            return

        if not self.date_deletion_requested:
            logger.error(
                "User.anonymize_or_delete called, but deletion of pk=%s hasn't been requested",
                self.pk,
            )
            return

        if subscriptions.queries.has_not_yet_cancelled_subscription(self):
            logger.error(
                "User.anonymize_or_delete called, but pk=%s has not yet cancelled subscriptions",
                self.pk,
            )
            return

        if self.image:
            try:
                self.image.delete(save=False)
            except Exception:
                logger.exception(
                    'Unable to delete image %s for pk=%s',
                    self.image.name,
                    self.pk,
                )

        # If there are no orders, the user account can be deleted
        if self.order_set.count() == 0:
            logger.warning(
                'User pk=%s requested deletion and has no orders: deleting the account',
                self.pk,
            )
            self.delete()
            return

        logger.warning(
            'User pk=%s requested deletion and has orders: anonymizing the account',
            self.pk,
        )
        username = f'del{shortuid()}'
        self.__class__.objects.filter(pk=self.pk).update(
            email=f'{username}@example.com',
            full_name='',
            username=username,
            badges=None,
            is_subscribed_to_newsletter=False,
            is_active=False,
            image=None,
        )
        logger.warning('Anonymized user pk=%s', self.pk)

        logger.warning('Soft-deleting payment methods records of user pk=%s', self.pk)
        for payment_method in self.paymentmethod_set.all():
            payment_method.recognisable_name = '<deleted>'
            logger.warning(
                'Deleting payment method %s of user pk=%s at the payment gateway',
                payment_method.pk,
                self.pk,
            )
            payment_method.delete()

        logger.warning('Deleting address records of user pk=%s', self.pk)
        looper.models.Address.objects.filter(user_id=self.pk).delete()

        logger.warning('Deleting customer records of user pk=%s', self.pk)
        looper.models.Customer.objects.filter(user_id=self.pk).delete()
        looper.models.GatewayCustomerId.objects.filter(user_id=self.pk).delete()

        logger.warning('Anonymizing comments of user pk=%s', self.pk)
        self.comments.update(user_id=None)

        logger.warning('Anonymizing likes of user pk=%s', self.pk)
        self.like_set.update(user_id=None)

        logger.warning('Deleting actions of user pk=%s', self.pk)
        self.actor_actions.all().delete()

        message = 'Anonymized because account deletion was requested'
        admin_log.attach_log_entry(self, message)


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
