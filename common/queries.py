from typing import Optional, Union, Dict, List

from django.contrib.auth.models import User
from django.core import paginator
from django.db.models import QuerySet
from django.db.models.base import Model
from django.db.models.expressions import Value
from django.db.models.fields import CharField

from films.models import ProductionLog
from training.models import Training
from blog.models import Post

DEFAULT_FEED_PAGE_SIZE = 10
# Certain permissions can be defined by multiple groups
EQUIVALENT_GROUPS = {
    'subscriber': ['demo'],
}


def get_activity_feed_page(
    page_number: Optional[Union[int, str]] = 1,
    per_page: Optional[Union[int, str]] = DEFAULT_FEED_PAGE_SIZE,
) -> paginator.Page:
    """Fetch a page of the latest Post, Production Log, and Training objects.

    The objects are sorted by their date_created attribute.
    The code has been adopted from the post:
    https://simonwillison.net/2018/Mar/25/combined-recent-additions/

    Args:
        page_number: (optional) int or str; activity feed page number, used by the
            paginator. By default, the first page.
        per_page: (optional) int or str; the number of records to display per page, used
            by the paginator. Defaults to DEFAULT_FEED_PAGE_SIZE.

    Returns:
        A Page object of 'records'. A record is a dictionary representing one object:
        a blog Post, a Production Log, or a Training.
        The dictionary has the following keys:
            'pk': int - the primary key of the related object,
            'date_created': datetime - the date when the object was created,
            'obj_type': str - specifies the type (model) of the object,
            'object': a particular Model instance.
        E.g.:
            {'pk': 2,
            'date_created': datetime.datetime(2020, 7, 8, 21, 28, 13, 128989, tzinfo=<UTC>),
            'obj_type': 'production log',
            'object': <ProductionLog: Coffee Run Production Weekly 2020-04-28>}
    """
    records = (
        Post.objects.annotate(obj_type=Value('post', output_field=CharField()))
        .values('pk', 'date_created', 'obj_type')
        .union(
            ProductionLog.objects.annotate(
                obj_type=Value('production log', output_field=CharField())
            ).values('pk', 'date_created', 'obj_type'),
            Training.objects.annotate(obj_type=Value('training', output_field=CharField())).values(
                'pk', 'date_created', 'obj_type'
            ),
        )
    ).order_by('-date_created')

    page_number = int(page_number) if page_number else 1
    per_page = int(per_page) if per_page else DEFAULT_FEED_PAGE_SIZE
    p = paginator.Paginator(records, per_page)
    records_page = p.get_page(page_number)

    obj_type_to_queryset: Dict[str, 'QuerySet[Model]'] = {
        'post': Post.objects.select_related('author'),
        'production log': ProductionLog.objects.select_related('film'),
        'training': Training.objects,
    }

    # Collect the pks we need to load for each obj_type:
    to_load: Dict[str, List[int]] = {}
    for record in records_page:
        to_load.setdefault(record['obj_type'], []).append(record['pk'])

    # Fetch them
    fetched = {}
    for obj_type, pks in to_load.items():
        for obj in obj_type_to_queryset[obj_type].filter(pk__in=pks):
            fetched[(obj_type, obj.pk)] = obj

    # Annotate 'records_page' with loaded objects
    for record in records_page:
        key = (record['obj_type'], record['pk'])
        record['object'] = fetched[key]

    return records_page


def has_group(user: User, group_name: str) -> bool:
    """Check if given user is assigned to a given group, or its equivalent."""
    if not user or user.is_anonymous:
        return False
    equivalent_groups = {group_name, *EQUIVALENT_GROUPS.get(group_name, [])}
    return user.groups.filter(name__in=equivalent_groups).exists()
