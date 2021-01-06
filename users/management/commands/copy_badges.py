"""Fetch and save profile images from Blender ID."""
import logging

from django.db.models import F
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from users.blender_id import BIDSession

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
bid = BIDSession()


class Command(BaseCommand):
    """Command for updating user badges."""

    def handle(self, *args, **options):  # noqa: D102
        query = User.objects.filter(
            oauth_info__user_id__isnull=False,
            oauth_tokens__access_token__isnull=False,
        ).order_by(F('last_login').desc(nulls_last=True))
        seen_ids = set()
        logger.info('%s records to update total', query.count())
        for user in query:
            # Joins and order_by produce duplicates
            if user.pk in seen_ids:
                continue
            bid.copy_badges_from_blender_id(user=user)
            seen_ids.add(user.pk)
