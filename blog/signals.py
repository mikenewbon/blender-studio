import logging

from actstream import action
from django.db.models.signals import post_save
from django.dispatch import receiver

from blog.models import PostComment, Like


logger = logging.getLogger(__name__)


@receiver(post_save, sender=PostComment)
def notify_about_comment(
    sender: object, instance: PostComment, created: bool, **kwargs: object
) -> None:
    """
    Generate notifications about comments under blog posts.

    Because asset <-> comment relation uses a custom through model (PostComment),
    film asset is not accessible in post_save of a Comment, only in post_save of the through model.
    """
    if not created:
        return

    instance.comment.create_action()


@receiver(post_save, sender=Like)
def notify_about_like(sender: object, instance: Like, created: bool, **kwargs: object) -> None:
    """Generate notifications about blog post likes."""
    if not created:
        return

    # Don't notify when one likes their own blog post
    if instance.user == instance.post.author:
        return

    action.send(instance.user, verb='liked', target=instance.post, public=False)
