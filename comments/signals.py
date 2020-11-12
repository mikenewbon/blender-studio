import logging

from actstream import action
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from comments.models import Comment, Like
from common import markdown

logger = logging.getLogger(__name__)


def _create_action_from_comment(user, comment: Comment, verb: str) -> None:
    target = comment.get_action_target()

    action.send(user, verb=verb, action_object=comment, target=target, public=False)


@receiver(pre_save, sender=Comment)
def clean_message(sender: object, instance: Comment, **kwargs: object) -> None:
    """Clean comment message and pre-render HTML for it."""
    instance.message = markdown.sanitize(instance.message)
    instance.message_html = markdown.render(instance.message)


@receiver(post_save, sender=Like)
def notify_about_like(sender: object, instance: Like, created: bool, **kwargs: object) -> None:
    """Generate notifications about comments likes."""
    if not created:
        return

    # Don't notify when one likes their own comments
    if instance.user == instance.comment.user:
        return

    _create_action_from_comment(instance.user, instance.comment, verb='liked')


@receiver(post_save, sender=Comment)
def notify_about_reply(sender: object, instance: Comment, created: bool, **kwargs: object) -> None:
    """Generate notifications about comment replies."""
    if not created:
        return

    if not instance.reply_to:
        return

    # Don't notify when one replies to their own comments
    if instance.reply_to.user == instance.user:
        return

    _create_action_from_comment(instance.user, instance.reply_to, verb='replied to')
