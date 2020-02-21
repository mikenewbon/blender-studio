import datetime
import json

from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from training_main.queries.progress import set_video_progress
from training_main.views.decorators import login_required


@require_POST
@login_required
def video_progress(request: HttpRequest, *, video_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    position = datetime.timedelta(seconds=float(parsed_body['position']))

    set_video_progress(user_pk=request.user.id, video_pk=video_pk, position=position)

    return JsonResponse({'position': position.total_seconds()})
