import json

from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.views.decorators.http import require_POST

from training.queries.progress import (
    set_section_progress_started,
    set_section_progress_finished,
)


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
