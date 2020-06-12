from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render

from films.models import Asset


def asset(request: HttpRequest, film_pk: int, asset_pk: int) -> HttpResponse:
    asset = (
        Asset.objects.filter(pk=asset_pk)
        .select_related(
            'static_asset',
            'collection',
            'static_asset__license',
            'static_asset__author',
            'static_asset__user',
        )
        .get()
    )

    return render(request, 'components/modal_asset.html', {'asset': asset})
