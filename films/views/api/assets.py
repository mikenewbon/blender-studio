import json
from typing import Optional

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.http.response import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe, require_POST

from comments.models import Comment
from common.types import assert_cast
from films.models import Asset, AssetComment
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

    context = get_asset_context(asset, request.GET.get('site_context'), request.user)

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


@require_POST
@login_required
def comment(request: HttpRequest, *, asset_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    reply_to_pk = None if parsed_body['reply_to'] is None else int(parsed_body['reply_to'])
    message = assert_cast(str, parsed_body['message'])

    @transaction.atomic
    def create_comment(
        *, user_pk: int, asset_pk: int, message: str, reply_to_pk: Optional[int]
    ) -> Comment:
        comment = Comment.objects.create(user_id=user_pk, message=message, reply_to_id=reply_to_pk)
        AssetComment.objects.create(comment_id=comment.id, asset_id=asset_pk)
        return comment

    comment = create_comment(
        user_pk=request.user.pk, asset_pk=asset_pk, message=message, reply_to_pk=reply_to_pk
    )

    return JsonResponse(
        {
            'id': comment.pk,
            'full_name': comment.full_name,
            'profile_image_url': 'https://blender.chat/avatar/fsiddi',
            'date_string': comment.date_created.strftime('%d %B %Y - %H:%M'),
            'message': comment.message,
            'like_url': comment.like_url,
            'liked': False,
            'likes': 0,
            'edit_url': comment.edit_url,
            'delete_url': comment.delete_url,
        }
    )
