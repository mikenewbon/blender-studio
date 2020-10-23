import datetime as dt

from django.db.models import QuerySet, Subquery
from django.db.models.expressions import Case, When, F
from django.db.models.fields import BooleanField
from django.utils import timezone

from blog.models import Revision


def get_latest_post_revisions(limit: int = 12) -> 'QuerySet[Revision]':
    """Return the newest published revisions of all published posts, newest posts first."""
    return (
        Revision.objects.filter(
            pk__in=Subquery(
                Revision.objects.filter(is_published=True, post__is_published=True)
                # Include only the latest revision for each post:
                .order_by('post_id', '-post__date_published')
                .distinct('post_id')
                .values('pk')
            )
        )
        .annotate(
            slug=F('post__slug'),
            is_new=Case(
                When(post__date_created__gte=timezone.now() - dt.timedelta(days=7), then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )
        .order_by('-post__date_published')
    )[:limit]
