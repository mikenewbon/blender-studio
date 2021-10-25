"""Comment API used in content gallery."""
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from comments.views.common import comment_response
from common.decorators import subscription_required
from films.models import AssetComment


@require_POST
@login_required
@subscription_required
def comment(request: HttpRequest, *, asset_pk: int) -> JsonResponse:
    """Add a top-level comment or a reply to another comment under an asset in content gallery."""
    return comment_response(request, AssetComment, 'asset_id', asset_pk)
