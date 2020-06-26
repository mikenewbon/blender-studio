from enum import Enum
from typing import Dict, Union, cast, List, Optional

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Asset, Collection


class SiteContexts(Enum):
    """Defines possible values of the site_context query parameter."""

    WEEKLIES = 'weeklies'
    FEATURED_ARTWORK = 'featured_artwork'
    GALLERY = 'gallery'


def get_previous_asset_in_weeklies(asset: Asset) -> Asset:
    current_log_entry = asset.entry_asset.production_log_entry
    try:
        previous_asset = asset.get_previous_by_date_created(
            entry_asset__production_log_entry=current_log_entry, is_published=True,
        )
    except Asset.DoesNotExist:
        previous_asset = cast(
            Asset,
            Asset.objects.filter(
                entry_asset__production_log_entry=current_log_entry, is_published=True,
            )
            .order_by('date_created')
            .last(),
        )
    return previous_asset


def get_next_asset_in_weeklies(asset: Asset) -> Asset:
    current_log_entry = asset.entry_asset.production_log_entry
    try:
        next_asset = asset.get_next_by_date_created(
            entry_asset__production_log_entry=current_log_entry, is_published=True,
        )
    except Asset.DoesNotExist:
        next_asset = cast(
            Asset,
            Asset.objects.filter(
                entry_asset__production_log_entry=current_log_entry, is_published=True,
            )
            .order_by('date_created')
            .first(),
        )
    return next_asset


def get_previous_asset_in_featured_artwork(asset: Asset) -> Asset:
    try:
        previous_asset = asset.get_previous_by_date_created(
            film=asset.film, is_published=True, is_featured=True
        )
    except Asset.DoesNotExist:
        previous_asset = cast(
            Asset,
            Asset.objects.filter(film=asset.film, is_published=True, is_featured=True)
            .order_by('date_created')
            .last(),
        )
    return previous_asset


def get_next_asset_in_featured_artwork(asset: Asset) -> Asset:
    try:
        next_asset = asset.get_next_by_date_created(
            film=asset.film, is_published=True, is_featured=True
        )
    except Asset.DoesNotExist:
        next_asset = cast(
            Asset,
            Asset.objects.filter(film=asset.film, is_published=True, is_featured=True)
            .order_by('date_created')
            .first(),
        )
    return next_asset


def get_previous_asset_in_gallery(asset: Asset) -> Asset:
    collection = cast(Collection, asset.collection)
    collection_assets = list(collection.assets.order_by('order', 'date_created'))
    asset_index = collection_assets.index(asset)
    return collection_assets[asset_index - 1]


def get_next_asset_in_gallery(asset: Asset) -> Asset:
    collection = cast(Collection, asset.collection)
    collection_assets: List[Asset] = list(collection.assets.order_by('order', 'date_created'))
    asset_index = collection_assets.index(asset)
    return collection_assets[(asset_index + 1) % len(collection_assets)]


def get_asset_context(
    asset: Asset, site_context: Optional[str]
) -> Dict[str, Union[Asset, str, None]]:
    """Creates context for the api-asset view: the current, previous and next assets.

    The request's URL is expected to contain a query string 'site_context=...' with one
    of the following values (see the SiteContexts enum):
    - 'weeklies' - for assets inside production log entries in the 'Weeklies' website section;
        they are sorted by their `date_created`,
    - 'featured_artwork' - for featured assets in the 'Gallery' section; they are sorted by
        their `date_created`,
    - 'gallery' - for assets inside collections in the 'Gallery section; they are sorted by
        their `order` and `date_created` (`order` may not define an unambiguous order).
    If there is no 'site_context' parameter, or it has another value, the previous and next
    assets are set to the current asset.

    If the current asset is the first one in the given context, previous_asset is set
    to the last one in the context. If the current asset is the last one, its next_asset
    will be the first in the context.

    The name 'site_context' is to be distinguishable from the '(template) context' variable.

    Args:
        asset: the asset to be displayed in the modal;
        site_context: value retrieved from the query string's 'site_context' parameter;

    Returns:
        A dictionary with the following keys:
        - 'asset' - the asset to display,
        - 'previous_asset' - the previous asset from the current context,
        - 'next_asset' - the next asset from the current context,
        - 'site_context' - a string; it can be reused in HTML components which need to add
        a query string to the asset modal URL.
    """
    if site_context == SiteContexts.WEEKLIES.value:
        previous_asset = get_previous_asset_in_weeklies(asset)
        next_asset = get_next_asset_in_weeklies(asset)
    elif site_context == SiteContexts.FEATURED_ARTWORK.value:
        previous_asset = get_previous_asset_in_featured_artwork(asset)
        next_asset = get_next_asset_in_featured_artwork(asset)
    elif site_context == SiteContexts.GALLERY.value:
        previous_asset = get_previous_asset_in_gallery(asset)
        next_asset = get_next_asset_in_gallery(asset)
    else:
        previous_asset = next_asset = asset

    context = {
        'asset': asset,
        'previous_asset': previous_asset,
        'next_asset': next_asset,
        'site_context': site_context,
    }

    return context


@require_safe
def asset(request: HttpRequest, asset_pk: int) -> HttpResponse:
    """Renders an asset modal, with the links to the previous and next assets."""
    asset = (
        Asset.objects.filter(pk=asset_pk)
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
    context = get_asset_context(asset, request.GET.get('site_context'))

    return render(request, 'common/components/modal_asset.html', context)


@require_safe
def asset_zoom(request: HttpRequest, asset_pk: int) -> HttpResponse:
    asset = Asset.objects.filter(pk=asset_pk).select_related('static_asset').get()

    return render(request, 'common/components/modal_asset_zoom.html', {'asset': asset})
