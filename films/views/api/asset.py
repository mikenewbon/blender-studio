from django.http import HttpResponse
from django.http.request import HttpRequest
from django.http.response import Http404
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Asset
from films.queries import get_asset_context


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
        asset = (
            Asset.objects.filter(pk=asset_pk, is_published=True)
            .select_related(
                'film',
                'collection',
                'static_asset',
                'static_asset__license',
                'static_asset__author',
                'static_asset__user',
                'static_asset__storage_location',
                'entry_asset__production_log_entry',
            )
            .get()
        )
    except Asset.DoesNotExist:
        raise Http404('No asset matches the given query.')

    context = get_asset_context(asset, request)

    return render(request, 'common/components/modal_asset.html', context)


@require_safe
def asset_zoom(request: HttpRequest, asset_pk: int) -> HttpResponse:
    try:
        asset = (
            Asset.objects.filter(pk=asset_pk, is_published=True)
            .select_related('static_asset__storage_location')
            .get()
        )
    except Asset.DoesNotExist:
        raise Http404('No asset matches the given query.')

    return render(request, 'common/components/modal_asset_zoom.html', {'asset': asset})
