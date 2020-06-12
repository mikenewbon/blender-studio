from django.http import JsonResponse
from django.http.request import HttpRequest
from django.shortcuts import render

from films.models import Asset


def asset(request: HttpRequest, film_pk: int, asset_pk: int):
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

    return JsonResponse(
        {
            'id': asset.pk,
            'name': asset.name,
            'type': asset.static_asset.source_type,
            'collection': asset.collection.name if asset.collection else None,
            'date_created': asset.date_created,
            'license': asset.static_asset.license.name,
            'author': asset.static_asset.author_name,
            'user': asset.static_asset.user.get_full_name(),
            'description': asset.description,
            'source_url': asset.static_asset.source.url,
        }
    )
