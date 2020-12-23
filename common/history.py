"""Utilities for writing into Django's "admin history"."""
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model


User = get_user_model()


def log_change(target, msg: str):
    """Logs a change to a given object."""
    admin = User.objects.filter(is_superuser=True).order_by('id').first()
    LogEntry.objects.log_action(
        user_id=admin.pk,
        content_type_id=ContentType.objects.get_for_model(target).pk,
        object_id=target.pk,
        object_repr=str(target),
        action_flag=CHANGE,
        change_message=msg,
    )
