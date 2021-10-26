"""Character likes API."""
import json

from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from characters.models import Like
from common.types import assert_cast


@require_POST
@login_required
def character_like(request: HttpRequest, *, character_pk: int) -> JsonResponse:
    """Add or remove a like on a character with a given pk."""
    parsed_body = json.loads(request.body)
    requested_like = assert_cast(bool, parsed_body['like'])

    if requested_like:
        Like.objects.update_or_create(character_id=character_pk, user_id=request.user.id)
    else:
        Like.objects.filter(character_id=character_pk, user_id=request.user.id).delete()

    number_of_likes = Like.objects.filter(character_id=character_pk).count()

    return JsonResponse({'like': requested_like, 'number_of_likes': number_of_likes})
