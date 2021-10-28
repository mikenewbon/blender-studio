from typing import Union

from django.db.models.signals import post_save
from django.dispatch import receiver

from characters.models import CharacterShowcaseComment, CharacterVersionComment


@receiver(post_save, sender=CharacterShowcaseComment)
@receiver(post_save, sender=CharacterVersionComment)
def notify_about_comment(
    sender: object,
    instance: Union[CharacterVersionComment, CharacterShowcaseComment],
    created: bool,
    **kwargs: object,
) -> None:
    """Generate notifications about comments under character versions or showcases."""
    if not created:
        return

    instance.comment.create_action()
