"""Fetch and save profile images from Blender ID."""
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Command for fetching and saving images for accounts that don't have any."""

    def handle(self, *args, **options):  # noqa: D102
        query = User.objects.filter(last_login__isnull=False, profile__image__isnull=True).order_by(
            '-last_login'
        )
        logger.info('%s records to update total', query.count())
        for user in query:
            if user.image:
                continue  # already has an image, skipping
            user.copy_avatar_from_blender_id()
