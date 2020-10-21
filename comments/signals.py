import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver
import bleach

from comments.models import Comment
from common import markdown

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Comment)
def clean_message(sender: object, instance: Comment, **kwargs: object) -> None:
    """Clean comment message and pre-render HTML for it."""
    instance.message = bleach.clean(instance.message)
    instance.message_html = markdown.render(instance.message)
