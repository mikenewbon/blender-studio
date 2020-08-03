import datetime as dt

from django.db.models import QuerySet
from django.db.models.expressions import Case, When, F
from django.db.models.fields import BooleanField
from django.utils import timezone

from blog.models import Revision


def get_latest_post_revisions() -> 'QuerySet[Revision]':
    """Returns the newest published revisions of all published post."""
    return (
        Revision.objects.filter(is_published=True, post__is_published=True)
        .order_by('post_id', '-date_created')
        .distinct('post_id')
        .annotate(
            slug=F('post__slug'),
            is_new=Case(
                When(post__date_created__gte=timezone.now() - dt.timedelta(days=7), then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )
        .select_related('storage_location')
    )
