import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.http.response import Http404
from django.http.response import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_safe

from common.types import assert_cast
from films.models import Asset
from films.queries import get_asset_context, get_asset, set_asset_like
from stats.models import StaticAssetView


@require_safe
def asset(request: HttpRequest, asset_pk: int) -> HttpResponse:
    """Renders a :model:`films.Asset` modal, with the links to the previous and next assets.

    **Context**
        ``asset``
            The asset to display.
        ``previous_asset``
            The previous asset from the current site context.
        ``next_asset``
            The next asset from the current site context.
        ``site_context``
            A string specifying in which page the asset modal is opened; it can be reused
            in HTML components which need to add a query string to the asset modal URL.
        ``comments``
            A typed_templates.Comments instance with the asset's comments.
        ``user_can_edit_asset``
            A bool specifying whether the current user is able to edit the displayed asset.

    **Template**
        :template:`common/components/modal_asset.html`
    """
    try:
        asset = get_asset(asset_pk, request)
    except Asset.DoesNotExist:
        raise Http404('No asset matches the given query.')

    context = get_asset_context(asset, request)

    StaticAssetView.create_from_request(request, asset.static_asset_id)
    return render(request, 'common/components/modal_asset.html', context)


@require_safe
def asset_zoom(request: HttpRequest, asset_pk: int) -> HttpResponse:
    try:
        asset = get_asset(asset_pk, request)
    except Asset.DoesNotExist:
        raise Http404('No asset matches the given query.')

    StaticAssetView.create_from_request(request, asset.static_asset_id)
    return render(request, 'common/components/modal_asset_zoom.html', {'asset': asset})


@require_POST
@login_required
def asset_like(request: HttpRequest, *, asset_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    requested_like = assert_cast(bool, parsed_body['like'])

    number_of_likes = set_asset_like(
        asset_pk=asset_pk, user_pk=request.user.pk, like=requested_like
    )
    return JsonResponse({'like': requested_like, 'number_of_likes': number_of_likes})
