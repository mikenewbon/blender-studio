import datetime
import json

from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from training_main.models.progress import UserVideoProgress
from training_main.queries.progress import (
    set_video_progress,
    set_section_progress_started,
    set_section_progress_finished,
)
from training_main.queries.sections import video_from_pk
from training_main.views.decorators import login_required


@require_POST
@login_required
def video_progress(request: HttpRequest, *, video_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    position = datetime.timedelta(seconds=float(parsed_body['position']))
    set_video_progress(user_pk=request.user.id, video_pk=video_pk, position=position)

    video = video_from_pk(video_pk=video_pk)
    set_section_progress_started(user_pk=request.user.id, section_pk=video.section_id)

    if position / video.duration > UserVideoProgress.section_completion_fraction:
        set_section_progress_finished(user_pk=request.user.id, section_pk=video.section_id)

    return JsonResponse({'position': position.total_seconds()})


@require_POST
@login_required
def section_progress(request: HttpRequest, *, section_pk: int) -> JsonResponse:
    parsed_body = json.loads(request.body)

    assert parsed_body['status'] in {'started', 'finished'}
    status = parsed_body['status']

    if status == 'started':
        set_section_progress_started(user_pk=request.user.id, section_pk=section_pk)
    elif status == 'finished':
        set_section_progress_finished(user_pk=request.user.id, section_pk=section_pk)

    return JsonResponse({'status': status})
