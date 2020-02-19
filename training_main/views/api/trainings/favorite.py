import json

from django.http import JsonResponse
from django.http.request import HttpRequest
from django.views.decorators.http import require_POST

from training_main.queries.trainings import set_favorite
from training_main.views.decorators import login_required


@require_POST
@login_required
def favorite(request: HttpRequest, *, training_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)
    requested_favorite = bool(parsed_body['favorite'])
    set_favorite(training_pk=training_pk, user_pk=request.user.pk, favorite=requested_favorite)
    return JsonResponse({'favorite': requested_favorite})
