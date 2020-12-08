"""Fetch and save profile images from Blender ID."""
import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Command for fetching and saving profile images for accounts that don't have any."""

    def handle(self, *args, **options):  # noqa: D102
        query = User.objects.filter(last_login__isnull=False, profile__image__isnull=True).order_by(
            '-last_login'
        )
        logger.info('%s records to update total', query.count())
        for user in query:
            if not getattr(user, 'profile', None):
                logger.error('%s, id=%s is missing a Profile record', user, user.pk)
                continue
            if user.profile.image:
                continue  # already has profile image, skipping
            user.profile.copy_avatar_from_blender_id()
