"""Comments API for characters."""
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from characters.models import CharacterVersionComment, CharacterShowcaseComment
from comments.views.common import comment_response
from common.decorators import subscription_required


@require_POST
@login_required
@subscription_required
def comment_version(request: HttpRequest, *, character_version_pk: int) -> JsonResponse:
    """Add a top-level comment or a reply to another comment under a character version."""
    return comment_response(
        request, CharacterVersionComment, 'character_version_id', character_version_pk
    )


@require_POST
@login_required
@subscription_required
def comment_showcase(request: HttpRequest, *, character_showcase_pk: int) -> JsonResponse:
    """Add a top-level comment or a reply to another comment under a character showcase."""
    return comment_response(
        request, CharacterShowcaseComment, 'character_showcase_id', character_showcase_pk
    )
