from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Asset


@require_safe
def asset(request: HttpRequest, asset_pk: int) -> HttpResponse:
    """"""
    asset = (
        Asset.objects.filter(pk=asset_pk)
        .select_related(
            'film',
            'collection',
            'static_asset',
            'static_asset__license',
            'static_asset__author',
            'static_asset__user',
            'productionlogentryasset__production_log_entry',
        )
        .get()
    )

    # TODO(Natalia): refactor this
    if request.GET['context'] == 'weeklies':
        log_entry_assets = Asset.objects.filter(
            productionlogentryasset__production_log_entry=asset.productionlogentryasset.production_log_entry
        ).order_by('date_created')
        try:
            previous_asset = asset.get_previous_by_date_created(
                productionlogentryasset__production_log_entry=asset.productionlogentryasset.production_log_entry
            )
        except Asset.DoesNotExist:
            previous_asset = (
                Asset.objects.filter(
                    productionlogentryasset__production_log_entry=asset.productionlogentryasset.production_log_entry
                )
                .order_by('date_created')
                .last()
            )
        try:
            next_asset = asset.get_next_by_date_created(
                productionlogentryasset__production_log_entry=asset.productionlogentryasset.production_log_entry
            )
        except Asset.DoesNotExist:
            next_asset = (
                Asset.objects.filter(
                    productionlogentryasset__production_log_entry=asset.productionlogentryasset.production_log_entry
                )
                .order_by('date_created')
                .first()
            )
    elif request.GET['context'] == 'featured_artwork':
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
    else:  # the default context is the gallery
        collection_assets = Asset.objects.filter(
            is_published=True, collection=asset.collection
        ).order_by('order')

        previous_asset = collection_assets.filter(order__lt=asset.order).last()
        if not previous_asset:
            previous_asset = collection_assets.last()
        next_asset = collection_assets.filter(order__gt=asset.order).first()
        if not next_asset:
            next_asset = collection_assets.first()

    context = {
        'asset': asset,
        'previous_asset': previous_asset,
        'next_asset': next_asset,
    }

    return render(request, 'common/components/modal_asset.html', context, using='django')
