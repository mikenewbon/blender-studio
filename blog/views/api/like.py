import json

from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from blog.queries import set_post_like
from common.types import assert_cast


@require_POST
@login_required
def post_like(request: HttpRequest, *, post_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    requested_like = assert_cast(bool, parsed_body['like'])

    number_of_likes = set_post_like(post_pk=post_pk, user_pk=request.user.pk, like=requested_like)

    return JsonResponse({'like': requested_like, 'number_of_likes': number_of_likes})
