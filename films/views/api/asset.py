from typing import Dict, Union, Optional, List

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Asset


def get_previous_by_order_and_date_created(asset: Asset, collection_assets: List[Asset]) -> Asset:
    asset_index = collection_assets.index(asset)
    return collection_assets[asset_index - 1]


def get_next_by_order_and_date_created(asset: Asset, collection_assets: List[Asset]) -> Asset:
    asset_index = collection_assets.index(asset)
    return collection_assets[(asset_index + 1) % len(asset)]


def get_asset_context(asset: Asset, site_context: Optional[str]) -> Dict[str, Union[str, Asset]]:
    """Creates context for the api-asset view: the current, previous and next assets.

    The request's URL is expected to contain a query string 'site_context=...' with one
    of the following values:
    - 'weeklies' - for assets inside production log entries in the 'Weeklies' website section,
    - 'featured_artwork' - for featured assets in the 'Gallery' section,
    - 'gallery' - for assets inside collections in the 'Gallery section.
    If there is no 'site_context' parameter, or it has another value, the previous and next
    assets are set to the current asset.
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
    if site_context == 'weeklies':
        current_log_entry = asset.entry_asset.production_log_entry
        try:
            previous_asset = asset.get_previous_by_date_created(
                entry_asset__production_log_entry=current_log_entry, is_published=True,
            )
        except Asset.DoesNotExist:
            previous_asset = (
                Asset.objects.filter(
                    entry_asset__production_log_entry=current_log_entry, is_published=True,
                )
                .order_by('date_created')
                .last()
            )
        try:
            next_asset = asset.get_next_by_date_created(
                entry_asset__production_log_entry=current_log_entry, is_published=True,
            )
        except Asset.DoesNotExist:
            next_asset = (
                Asset.objects.filter(
                    entry_asset__production_log_entry=current_log_entry, is_published=True,
                )
                .order_by('date_created')
                .first()
            )
    elif site_context == 'featured_artwork':
        try:
            previous_asset = asset.get_previous_by_date_created(
                film=asset.film, is_published=True, is_featured=True
            )
        except Asset.DoesNotExist:
            previous_asset = (
                Asset.objects.filter(film=asset.film, is_published=True, is_featured=True)
                .order_by('date_created')
                .last()
            )
        try:
            next_asset = asset.get_next_by_date_created(
                film=asset.film, is_published=True, is_featured=True
            )
        except Asset.DoesNotExist:
            next_asset = (
                Asset.objects.filter(film=asset.film, is_published=True, is_featured=True)
                .order_by('date_created')
                .first()
            )
    elif site_context == 'gallery':
        collection_assets = list(
            Asset.objects.filter(is_published=True, collection=asset.collection).order_by(
                'order', 'date_created'
            )
        )
        previous_asset = get_previous_by_order_and_date_created(asset, collection_assets)
        next_asset = get_next_by_order_and_date_created(asset, collection_assets)
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
    """This view renders an asset modal, with the links to the previous and next assets."""
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
    print('site_context', request.GET.get('site_context'), "\n", context)

    return render(request, 'common/components/modal_asset.html', context)


@require_safe
def asset_zoom(request: HttpRequest, asset_pk: int) -> HttpResponse:
    asset = Asset.objects.filter(pk=asset_pk).select_related('static_asset').get()

    return render(request, 'common/components/modal_asset_zoom.html', {'asset': asset})
