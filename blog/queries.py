import datetime as dt

from django.db.models import OuterRef, Subquery, QuerySet
from django.db.models.expressions import Case, When
from django.db.models.fields import BooleanField
from django.utils import timezone

from blog.models import Revision, Post


def get_posts_with_latest_revision() -> 'QuerySet[Post]':
    newest_revision = Revision.objects.filter(is_published=True, post=OuterRef('pk')).order_by(
        '-date_created'
    )[:1]
    return (
        Post.objects.filter(is_published=True)
        .order_by('-date_created')
        .annotate(
            title=Subquery(newest_revision.values_list('title')),
            topic=Subquery(newest_revision.values_list('topic')),
            description=Subquery(newest_revision.values_list('description')),
            html_content=Subquery(newest_revision.values_list('html_content')),
            is_new=Case(
                When(date_created__gte=timezone.now() - dt.timedelta(days=7), then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )
        .prefetch_related('revisions')
    )
