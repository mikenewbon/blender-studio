from enum import Enum
from typing import List, Optional, cast, Dict, Union, Any
import logging
import random

from django.contrib.auth import get_user_model
from django.core import paginator
from django.db.models.query import Prefetch, QuerySet
from django.http.request import HttpRequest

from comments import typed_templates
from comments.models import Comment
from comments.queries import get_annotated_comments
from comments.views.common import comments_to_template_type
from films.models import Asset, Collection, Film, ProductionLogEntryAsset, Like, ProductionLog
import common.queries

User = get_user_model()
logger = logging.getLogger(__name__)
DEFAULT_LOGS_PAGE_SIZE = 3


class SiteContexts(Enum):
    """Defines possible values of the site_context query parameter."""

    PRODUCTION_LOGS = 'production_logs'
    FEATURED_ARTWORK = 'featured_artwork'
    GALLERY = 'gallery'


def get_featured_assets(film: Film) -> QuerySet:
    """Retrieve film's featured assets."""
    return film.assets.filter(is_published=True, is_featured=True).order_by('-date_published')


def _get_other_assets_in_collection(asset: Asset) -> QuerySet:
    collection = cast(Collection, asset.collection)
    return collection.assets.filter(is_published=True).order_by(*Asset._meta.ordering)


def _get_assets_in_production_log_entry(asset: Asset) -> QuerySet:
    return asset.entry_asset.production_log_entry.assets.filter(is_published=True).order_by(
        *Asset._meta.ordering
    )


def _get_previous_in_query(q: QuerySet, instance: Asset) -> Optional[Asset]:
    """Fetch a record previous from this one in the given query.

    Because some records, such as assets, must be ordered by multiple columns,
    ORM's `get_previous_by_FOO` cannot be used.
    See https://code.djangoproject.com/ticket/16505 for more details.
    """
    result_list = list(q)
    instance_index = result_list.index(instance)
    if instance_index == 0:
        return None
    return result_list[instance_index - 1]


def _get_next_in_query(q: QuerySet, instance: Asset) -> Optional[Any]:
    """Fetch a record next to this one in the given query.

    Because some records, such as assets, must be ordered by multiple columns,
    ORM's `get_next_by_FOO` cannot be used.
    See https://code.djangoproject.com/ticket/16505 for more details.
    """
    result_list = list(q)
    instance_index = result_list.index(instance)
    if instance_index == len(result_list) - 1:
        return None
    return result_list[instance_index + 1]


def get_previous_asset_in_production_logs(asset: Asset) -> Optional[Asset]:  # noqa: D103
    current_log_entry_assets = _get_assets_in_production_log_entry(asset)
    return _get_previous_in_query(current_log_entry_assets, asset)


def get_next_asset_in_production_logs(asset: Asset) -> Optional[Asset]:  # noqa: D103
    current_log_entry_assets = _get_assets_in_production_log_entry(asset)
    return _get_next_in_query(current_log_entry_assets, asset)


def get_previous_production_log(production_logs, production_log):  # noqa: D103
    return _get_previous_in_query(production_logs, production_log)


def get_next_production_log(production_logs, production_log):  # noqa: D103
    return _get_next_in_query(production_logs, production_log)


def get_previous_asset_in_featured_artwork(asset: Asset) -> Optional[Asset]:
    """Fetch asset previous from this one in featured film assets."""
    featured_assets = get_featured_assets(asset.film)
    return _get_previous_in_query(featured_assets, asset)


def get_next_asset_in_featured_artwork(asset: Asset) -> Optional[Asset]:
    """Fetch asset next from this one in featured film assets."""
    featured_assets = get_featured_assets(asset.film)
    return _get_next_in_query(featured_assets, asset)


def get_previous_asset_in_gallery(asset: Asset) -> Optional[Asset]:
    """Fetch asset previous from this one in this asset's collection."""
    collection_assets = _get_other_assets_in_collection(asset)
    return _get_previous_in_query(collection_assets, asset)


def get_next_asset_in_gallery(asset: Asset) -> Optional[Asset]:
    """Fetch asset next from this one in the this asset's collection."""
    collection_assets = _get_other_assets_in_collection(asset)
    return _get_next_in_query(collection_assets, asset)


def get_asset_context(
    asset: Asset, request: HttpRequest
) -> Dict[str, Union[Asset, typed_templates.Comments, str, None, bool]]:
    """Create context for the api-asset view: the current, previous and next published assets.

    The request's URL is expected to contain a query string 'site_context=...' with one
    of the following values (see the SiteContexts enum):
    - 'production_logs' - for assets inside production log entries in the 'Weeklies' website
        section;
    - 'featured_artwork' - for featured assets in the 'Gallery' section;
    - 'gallery' - for assets inside collections in the 'Gallery section.
    In every context, assets are sorted by their `order` and `date_published`.
    If 'site_context' parameter has another value, is not provided, or the current asset
    is the first one or the last one in the given context, the previous and next
    assets are set to None.

    The name 'site_context' is to be distinguishable from the '(template) context' variable.

    Args:
        asset: the asset to be displayed in the modal;
        request: an HTTP request.

    Returns:
        A dictionary with the following keys:
        - 'asset' - the asset to display,
        - 'previous_asset' - the previous asset from the current context,
        - 'next_asset' - the next asset from the current context,
        - 'site_context' - a string; it can be reused in HTML components which need to add
        a query string to the asset modal URL,
        - 'comments' - a typed_templates.Comments instance with comments,
        - 'user_can_edit_asset' - a bool specifying whether the current user is able to edit
        the displayed asset in the admin panel.
    """
    site_context = request.GET.get('site_context')

    if site_context == SiteContexts.PRODUCTION_LOGS.value:
        previous_asset = get_previous_asset_in_production_logs(asset)
        next_asset = get_next_asset_in_production_logs(asset)
    elif site_context == SiteContexts.FEATURED_ARTWORK.value:
        previous_asset = get_previous_asset_in_featured_artwork(asset)
        next_asset = get_next_asset_in_featured_artwork(asset)
    elif site_context == SiteContexts.GALLERY.value:
        previous_asset = get_previous_asset_in_gallery(asset)
        next_asset = get_next_asset_in_gallery(asset)
    else:
        previous_asset = next_asset = None

    comments: List[Comment] = get_annotated_comments(asset, request.user.pk)

    context = {
        'asset': asset,
        'previous_asset': previous_asset,
        'next_asset': next_asset,
        'site_context': site_context,
        'comments': comments_to_template_type(comments, asset.comment_url, request.user),
        'user_can_edit_asset': (
            request.user.is_staff and request.user.has_perm('films.change_asset')
        ),
    }

    return context


def _get_asset_liked(asset: Asset = None, request: HttpRequest = None) -> Optional[Asset]:
    if not asset:
        return asset

    if request and request.user.is_authenticated:
        asset.liked = Like.objects.filter(asset_id=asset.pk, user_id=request.user.pk).exists()
    return asset


def get_asset_by_slug(slug: str, film_id: int, request: HttpRequest = None) -> Optional[Asset]:
    """Retrieve a published film asset by a given asset slug."""
    asset = (
        Asset.objects.filter(film_id=film_id, is_published=True, slug=slug)
        .select_related(
            'film',
            'collection',
            'static_asset',
            'static_asset__license',
            'static_asset__author',
            'static_asset__user',
            'entry_asset__production_log_entry',
        )
        .get()
    )
    return _get_asset_liked(asset, request)


def get_asset(asset_pk: int, request: HttpRequest = None) -> Optional[Asset]:
    """Retrieve a published film asset by a given asset ID."""
    asset = (
        Asset.objects.filter(pk=asset_pk, is_published=True)
        .select_related(
            'film',
            'collection',
            'static_asset',
            'static_asset__license',
            'static_asset__author',
            'static_asset__user',
            'entry_asset__production_log_entry',
        )
        .get()
    )

    return _get_asset_liked(asset, request)


def get_production_logs(film: Film) -> paginator.Page:
    """Retrieves film production logs.

    Args:
        film: A Film model instance

    Returns:
        A queryset containing production logs and all their related objects used in templates:
         - production log entries,
         - entries' authors and users (used to get each entry's author_name),
         - assets and static assets related to log entries. Note that entries' related
            `entry_assets` are available under the `assets` attribute (set in Prefetch).
            These objects are stored in a Python list, which is supposed to improve
            performance (see the note in the docs:
            https://docs.djangoproject.com/en/dev/ref/models/querysets/#django.db.models.Prefetch).
    """
    production_logs = (
        film.production_logs.order_by(*ProductionLog._meta.ordering)
        .select_related(
            'film',
        )
        .prefetch_related(
            'log_entries__author',
            'log_entries__user',
            'log_entries__production_log',
            'log_entries__production_log__film',
            'log_entries__production_log__film__filmcrew_set',
            Prefetch(
                'log_entries__entry_assets',
                queryset=ProductionLogEntryAsset.objects.select_related(
                    'asset__static_asset__video',
                ).order_by(*[f'asset__{field}' for field in Asset._meta.ordering]),
                to_attr='assets',
            ),
            'log_entries__assets__static_asset',
            'log_entries__assets__static_asset__contributors',
            'log_entries__assets__static_asset__image',
            'log_entries__assets__static_asset__video',
        )
    )
    return production_logs


def get_production_logs_page(
    film: Film,
    page_number: Optional[Union[int, str]] = 1,
    per_page: Optional[Union[int, str]] = DEFAULT_LOGS_PAGE_SIZE,
) -> paginator.Page:
    """Retrieves production logs page for film production logs context.

    Altogether, this function sends 5 database queries.

    Args:
        film: A Film model instance
        page_number: (optional) int or str; production logs page number, used by the
            paginator. By default, the first page.
        per_page: (optional) int or str; the number of logs to display per page, used
            by the paginator. Defaults to DEFAULT_LOGS_PAGE_SIZE.

    Returns:
        A queryset containing production logs and all their related objects used in templates:
         - production log entries,
         - entries' authors and users (used to get each entry's author_name),
         - assets and static assets related to log entries. Note that entries' related
            `entry_assets` are available under the `assets` attribute (set in Prefetch).
            These objects are stored in a Python list, which is supposed to improve
            performance (see the note in the docs:
            https://docs.djangoproject.com/en/dev/ref/models/querysets/#django.db.models.Prefetch).
    """
    production_logs = get_production_logs(film)

    page_number = int(page_number) if page_number else 1
    per_page = int(per_page) if per_page else DEFAULT_LOGS_PAGE_SIZE
    p = paginator.Paginator(production_logs, per_page)
    production_logs_page = p.get_page(page_number)

    return production_logs_page


def get_gallery_drawer_context(film: Film, user: User) -> Dict[str, Any]:
    """Retrieves collections for drawer menu in film gallery.

    The collections are ordered and nested, ready to be looped over in templates.
    Also the fake 'Featured Artwork' collection is created.
    This function sends TWO database queries (1: fetch film top-level collections,
    2: fetch their child collections, ordered).

    Args:
        film: A Film model instance.
        user: The currently logged-in user.
    Returns:
         A dictionary with the following keys:
        'collections': a dict of all the collections with their nested collections,
        'featured_artwork': a queryset of film assets marked as featured,
        'user_can_edit_collection': a bool specifying whether the current user
            should be able to edit collection items displayed in the drawer menu.
    """
    top_level_collections = (
        film.collections.filter(parent__isnull=True)
        .order_by(*Collection._meta.ordering)
        .prefetch_related(
            Prefetch(
                'child_collections',
                queryset=film.collections.order_by(*Collection._meta.ordering),
                to_attr='nested',
            )
        )
    )

    nested_collections: Dict[Collection, QuerySet[Collection]] = dict()
    for c in top_level_collections:
        nested_collections[c] = getattr(c, 'nested')

    return {
        'collections': nested_collections,
        'featured_artwork': get_featured_assets(film),
        'user_can_edit_collection': (user.is_staff and user.has_perm('films.change_collection')),
    }


def get_random_featured_assets(limit=8) -> List[Asset]:
    """Select a desired number of random featured film assets."""
    query = Asset.objects.filter(is_featured=True, is_published=True)
    featured_ids = tuple({row['id'] for row in query.values('id')})
    featured_ids_sample = random.sample(featured_ids, min(limit, len(featured_ids)))
    return list(query.filter(id__in=featured_ids_sample))


def get_current_asset(request: HttpRequest) -> Dict[str, Asset]:
    """Retrieve a film asset using an asset ID from the given request."""
    asset_pk = request.GET.get('asset')
    asset = None
    if asset_pk:
        try:
            asset = get_asset(int(asset_pk))
            return {'asset': asset}
        except Asset.DoesNotExist:
            logger.debug(f'Unable to find asset_pk={asset_pk}')
        except ValueError:
            logger.debug('Invalid asset_pk')
    return {}


def set_asset_like(*, asset_pk: int, user_pk: int, like: bool) -> int:
    """Like or unlike an asset."""
    if like:
        Like.objects.update_or_create(asset_id=asset_pk, user_id=user_pk)
    else:
        Like.objects.filter(asset_id=asset_pk, user_id=user_pk).delete()

    return Like.objects.filter(asset_id=asset_pk).count()


def should_show_landing_page(request: HttpRequest, film: Film) -> bool:
    """Return true if the given film is "locked" and a landing page should be shown for it."""
    return film.show_landing_page and (
        request.user.is_anonymous or not common.queries.has_active_subscription(request.user)
    )
