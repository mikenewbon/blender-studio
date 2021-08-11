"""A command for handling account deletion requests received via Blender ID.

Supposed to be called periodically via crontab or systemd timer.
"""
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

import users.tasks as tasks

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Handle account deletion requests received via Blender ID."""

    def handle(self, *args, **options):
        """Go through existing deletion requests, schedule handling of ones that are old enough."""
        prior_to = timezone.now() - tasks.DELETION_DELTA
        users_to_delete = User.objects.filter(
            date_deletion_requested__isnull=False,
            date_deletion_requested__lt=prior_to,
        ).exclude(  # exclude already processed records
            is_active=False,
        )
        user_ids = {user.pk for user in users_to_delete}
        if not len(user_ids):
            return
        logger.info('Found %s deletion requests that need handling', len(user_ids))
        for user_id in user_ids:
            tasks.handle_deletion_request(user_id)
