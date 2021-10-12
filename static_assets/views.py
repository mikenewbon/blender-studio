import datetime
import json
import logging
import mimetypes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http.request import HttpRequest
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
import requests

from static_assets.models.progress import UserVideoProgress
from static_assets.models import Video, VideoTrack
from training.queries.progress import (
    set_video_progress,
    set_section_progress_started,
    set_section_progress_finished,
)
from static_assets.coconut import events

log = logging.getLogger(__name__)


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


@require_POST
@csrf_exempt
def coconut_webhook(request, video_id):
    """Endpoint used by Coconut to update us on video processing."""
    if request.content_type != 'application/json':
        raise SuspiciousOperation('Coconut webhook endpoint was sent non-JSON data')
    job = json.loads(request.body)
    video = get_object_or_404(Video, pk=video_id)
    log.info('Updating video %i processing status: %s' % (video_id, job['event']))
    # On source.transferred
    if job['event'] == 'source.transferred':
        events.source_transferred(job, video)
    # On output.processed (thumbnail)
    elif job['event'] == 'output.processed' and job['format'] == 'jpg:1280x':
        events.output_processed_images(job, video)
    # On output.processed (video variation)
    elif job['event'] == 'output.processed' and 'mp4' in job['format']:
        events.output_processed_video(job, video)
    # On job.completed (unused for now)
    elif job['event'] == 'job.completed':
        # TODO: Add publishing logic
        pass
    return JsonResponse({'status': 'ok'})


@cache_page(60 * 15)
@require_GET
def video_track_view(request, pk: int, path: str):
    """Return track content.

    Video tracks served from a different domain require "crossorigin" attribute set on <video>,
    so tracks are served from the same domain to avoid having CORS set up at the CDN for
    all the videos as well as tracks.
    See https://developer.mozilla.org/en-US/docs/Web/HTML/Element/track#attr-src
    """
    track = get_object_or_404(VideoTrack, pk=pk, source=path)
    original_mimetype, _ = mimetypes.guess_type(track.source.name)
    with requests.get(track.source.url) as storage_response:
        response = HttpResponse(storage_response.content, content_type=original_mimetype)
        return response
