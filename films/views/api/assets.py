import json
from enum import Enum
from typing import Dict, Union, cast, Optional, List

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models.aggregates import Count
from django.db.models.expressions import Exists, OuterRef, Case, Value, When
from django.db.models.fields import BooleanField
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.http.response import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe, require_POST

from comments import typed_templates
from comments.models import Comment, Like
from comments.views.common import comments_to_template_type
from common.types import assert_cast
from films.models import Asset, Collection, AssetComment


class SiteContexts(Enum):
    """Defines possible values of the site_context query parameter."""

    PRODUCTION_LOGS = 'production_logs'
    FEATURED_ARTWORK = 'featured_artwork'
    GALLERY = 'gallery'


def get_previous_asset_in_production_logs(asset: Asset) -> Optional[Asset]:
    current_log_entry = asset.entry_asset.production_log_entry
    previous_asset: Optional[Asset]
    try:
        previous_asset = asset.get_previous_by_date_created(
            entry_asset__production_log_entry=current_log_entry, is_published=True,
        )
    except Asset.DoesNotExist:
        previous_asset = None
    return previous_asset


def get_next_asset_in_production_logs(asset: Asset) -> Optional[Asset]:
    current_log_entry = asset.entry_asset.production_log_entry
    next_asset: Optional[Asset]
    try:
        next_asset = asset.get_next_by_date_created(
            entry_asset__production_log_entry=current_log_entry, is_published=True,
        )
    except Asset.DoesNotExist:
        next_asset = None
    return next_asset


def get_previous_asset_in_featured_artwork(asset: Asset) -> Optional[Asset]:
    previous_asset: Optional[Asset]
    try:
        previous_asset = asset.get_previous_by_date_created(
            film=asset.film, is_published=True, is_featured=True
        )
    except Asset.DoesNotExist:
        previous_asset = None
    return previous_asset


def get_next_asset_in_featured_artwork(asset: Asset) -> Optional[Asset]:
    next_asset: Optional[Asset]
    try:
        next_asset = asset.get_next_by_date_created(
            film=asset.film, is_published=True, is_featured=True
        )
    except Asset.DoesNotExist:
        next_asset = None
    return next_asset


def get_previous_asset_in_gallery(asset: Asset) -> Optional[Asset]:
    collection = cast(Collection, asset.collection)
    collection_assets = list(collection.assets.filter(is_published=True).order_by('order', 'name'))
    asset_index = collection_assets.index(asset)
    if asset_index == 0:
        return None
    return collection_assets[asset_index - 1]


def get_next_asset_in_gallery(asset: Asset) -> Optional[Asset]:
    collection = cast(Collection, asset.collection)
    collection_assets = list(collection.assets.filter(is_published=True).order_by('order', 'name'))
    asset_index = collection_assets.index(asset)
    if asset_index == len(collection_assets) - 1:
        return None
    return collection_assets[(asset_index + 1)]


def get_asset_context(
    asset: Asset, site_context: Optional[str], user: User,
) -> Dict[str, Union[Asset, typed_templates.Comments, str, None]]:
    """Creates context for the api-asset view: the current, previous and next published assets.

    The request's URL is expected to contain a query string 'site_context=...' with one
    of the following values (see the SiteContexts enum):
    - 'production_logs' - for assets inside production log entries in the 'Weeklies' website
        section; they are sorted by their `date_created`,
    - 'featured_artwork' - for featured assets in the 'Gallery' section; they are sorted by
        their `date_created`,
    - 'gallery' - for assets inside collections in the 'Gallery section; they are sorted by
        their `order` and `name` (`order` may not define an unambiguous order).
    If 'site_context' parameter has another value, is not provided, or the current asset
    is the first one or the last one in the given context, the previous and next
    assets are set to None.

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

    comments: List[Comment] = get_comments(asset.pk, user.pk)
    user_is_moderator = user.has_perm('asset.moderate_comment')

    context = {
        'asset': asset,
        'previous_asset': previous_asset,
        'next_asset': next_asset,
        'site_context': site_context,
        'comments': comments_to_template_type(comments, asset.comment_url, user_is_moderator),
    }

    return context


def get_comments(asset_pk: int, user_pk: int) -> List[Comment]:
    """Fetch annotated comments for the asset given by the `asset_pk`."""
    comments = list(
        Comment.objects.filter(asset__pk=asset_pk)
        .annotate(
            liked=Exists(Like.objects.filter(comment_id=OuterRef('pk'), user_id=user_pk)),
            number_of_likes=Count('likes'),
            owned_by_current_user=Case(
                When(user_id=user_pk, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        .all()
    )
    return comments


@require_safe
def asset(request: HttpRequest, asset_pk: int) -> HttpResponse:
    """Renders an asset modal, with the links to the previous and next assets."""
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
            .prefetch_related('comments__user', 'comments__reply_to', 'comments__replies')
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
            'username': comment.username,
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
