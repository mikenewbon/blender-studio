import datetime
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from static_assets.models.progress import UserVideoProgress
from static_assets.models import Video
from training.queries.progress import (
    set_video_progress,
    set_section_progress_started,
    set_section_progress_finished,
)


@require_POST
@login_required
def video_progress(request: HttpRequest, *, video_pk: int) -> JsonResponse:
    # TODO(fsiddi) Relocate to static_assets app
    parsed_body = json.loads(request.body)

    position = datetime.timedelta(seconds=float(parsed_body['position']))
    set_video_progress(user_pk=request.user.id, video_pk=video_pk, position=position)

    # TODO(fsiddi) Separate this part, as section progress is specific to training
    video = Video.objects.get(pk=video_pk)
    try:
        section = video.static_asset.section
    except ObjectDoesNotExist:
        section = None

    if section:
        set_section_progress_started(user_pk=request.user.id, section_pk=section.id)

        if position / video.duration > UserVideoProgress.section_completion_fraction:
            set_section_progress_finished(user_pk=request.user.id, section_pk=section.id)

    return JsonResponse({'position': position.total_seconds()})
