import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.views.decorators.http import require_POST

from common.types import assert_cast
from training.queries.trainings import set_favorite


@require_POST
@login_required
def favorite(request: HttpRequest, *, training_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    requested_favorite = assert_cast(bool, parsed_body['favorite'])

    set_favorite(training_pk=training_pk, user_pk=request.user.pk, favorite=requested_favorite)

    return JsonResponse({'favorite': requested_favorite})
