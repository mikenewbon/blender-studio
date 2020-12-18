"""Rewrites ContentType of a new User model.

See https://code.djangoproject.com/ticket/25313#comment:18 for more details.
"""
import logging

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

User = get_user_model()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Command for fetching and saving profile images for accounts that don't have any."""

    def handle(self, *args, **options):  # noqa: D102
        auth_user = ContentType.objects.get(app_label='auth', model='User')
        new_user = ContentType.objects.get(app_label='users', model='User')

        for le in LogEntry.objects.filter(content_type=auth_user):
            le.content_type = new_user
            le.save()
