from typing import Optional, Union, Dict, List

from django.contrib.auth import get_user_model
from django.core import paginator
from django.db.models import QuerySet, Q
from django.db.models.base import Model
from django.db.models.expressions import Value
from django.db.models.fields import CharField

from blog.models import Post
from characters.models import Character
from films.models import ProductionLog, Asset, AssetCategory
from static_assets.models.static_assets import StaticAsset
from training.models import Training

User = get_user_model()
DEFAULT_FEED_PAGE_SIZE = 10


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
    """Check if given user is assigned to a given group."""
    if not user or user.is_anonymous:
        return False
    return user.groups.filter(name=group_name).exists()


def has_active_subscription(user: User) -> bool:
    """Check subscription status of the given user.

    Currently active subscription means having a custom `can_view_content` permission,
    given to users via different kinds of groups, for example:
     * "demo"
     * "subscriber"
     * "_org_<name>" for organisation-level subscriptions.
    """
    import subscriptions.queries

    if not user:
        return False

    # The old way, that supports Store-based and manual team subscriptions
    if user.has_perm('users.can_view_content'):
        return True

    # The new way, with subscriptions managed by Studio itself
    return subscriptions.queries.has_active_subscription(user)


def get_latest_trainings_and_production_lessons(production_lessons_limit=2, trainings_limit=10):
    """Return trainings and production lessons, mixed together ordered by latest."""
    latest_trainings = Training.objects.filter(is_published=True)[:trainings_limit]
    latest_production_lessons = Asset.objects.filter(
        category=AssetCategory.production_lesson, is_published=True
    ).order_by('-date_published')[:production_lessons_limit]
    return sorted(
        [*latest_trainings, *latest_production_lessons],
        key=lambda x: getattr(x, 'date_published', getattr(x, 'date_created', None)),
        reverse=True,
    )


def get_latest_characters():
    """Return latest characters."""
    return Character.objects.filter(is_published=True).order_by('-date_created')


def is_free_static_asset(static_asset_id: int) -> bool:
    """Return True if StaticAsset with given ID is linked to object that is free to download."""
    return (
        StaticAsset.objects.filter(pk=static_asset_id)
        .filter(
            Q(assets__is_free=True)
            | Q(section__is_free=True)
            | Q(character_versions__is_free=True)
            | Q(character_showcase__is_free=True)
        )
        .exists()
    )
