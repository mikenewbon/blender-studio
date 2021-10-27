from typing import Dict
import logging

from actstream.models import Action
from anymail.signals import tracking
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from blender_id_oauth_client import signals as bid_signals

from users.blender_id import BIDSession
from users.models import Notification
from users.queries import set_groups_from_roles
import users.tasks as tasks

User = get_user_model()
bid = BIDSession()
logger = logging.getLogger(__name__)


def _get_target_author(target) -> User:
    if getattr(target, 'author', None):
        return target.author
    # training `Section`s
    elif getattr(target, 'user', None):
        return target.user
    # film `Asset`s , `CharacterVersion` or `CharacterShowcase`
    elif getattr(target, 'static_asset', None):
        asset_author = target.static_asset.author or target.static_asset.user
        if asset_author:
            return asset_author


@receiver(bid_signals.user_created)
def update_user(
    sender: object, instance: User, oauth_info: Dict[str, str], **kwargs: object
) -> None:
    """Update a User when a new OAuth user is created.

    Copy 'full_name' from the received 'oauth_info' and attempt to copy avatar from Blender ID.
    """
    instance.full_name = oauth_info.get('full_name') or ''
    instance.save()

    group_names = oauth_info.get('roles') or []
    set_groups_from_roles(instance, group_names=group_names)

    bid.copy_avatar_from_blender_id(user=instance)
    bid.copy_badges_from_blender_id(user=instance)


@receiver(pre_save, sender=User)
def _sync_is_subscribed_to_newsletter(sender: object, instance: User, **kwargs):
    if not instance.pk:
        return

    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass
    else:
        if obj.is_subscribed_to_newsletter != instance.is_subscribed_to_newsletter:
            # State of newsletter subscription has changed
            tasks.handle_is_subscribed_to_newsletter(pk=instance.pk)


@receiver(tracking)
def _handle_mailgun_tracking_event(sender, event, esp_name, **kwargs):
    event_type = event.event_type
    event_data = event.esp_event.get('event-data', {})
    # Anymail doesn't recognize Mailgun's non-legacy Unsubscribed events for some reason
    if event_type == 'unknown':
        event_type = event_data.get('event', '').lower()
    should_unsubscribe = (
        event_type in ('unsubscribed', 'complained')
        or event_type in ('failed', 'bounced')
        and event_data.get('severity') == 'permanent'
    )
    if should_unsubscribe:
        tasks.handle_tracking_event_unsubscribe(event_type, event.message_id, event.esp_event)


@receiver(post_save, sender=Action)
def create_notification(sender: object, instance: Action, created: bool, **kwargs: object) -> None:
    """Create a Notification record to simplify retrieval of actions relevant to a user.

    Personal notifications include the following:
    * "someone commented on your blog post";
    * "someone liked your comment";
    * "someone replied to your comment";
    * TODO(anna): "someone saved your training section";
    * "someone commented on your training section";
    * "someone commented on your film asset";
    """
    if not created:
        return

    # There can be multiple users to whom this action is relevant
    users = set()
    action_object = instance.action_object
    verb = instance.verb
    target = instance.target

    # Notify about replies and comments likes
    if (
        action_object
        and getattr(action_object, 'user', None)
        and verb in [Action.objects.verb_replied, Action.objects.verb_liked]
    ):
        users.add(action_object.user)

    if target:
        target_author = _get_target_author(target)
        if target_author:
            # Notify about likes on blog posts and film assets
            if not action_object and verb in [Action.objects.verb_liked]:
                # Separate clause otherwise likes on related comments also end up in notifications
                users.add(target_author)

            # Notify about comments and likes on
            if verb in [Action.objects.verb_commented]:
                users.add(target_author)

    if not users:
        logger.debug(f'Unable to determine a relevant user for a new action: {instance}')
        return

    for user in users:
        # Don't notify yourself about your own actions: they can be viewed in activity
        if user == instance.actor:
            continue
        notification = Notification(user=user, action=instance)
        notification.save()
