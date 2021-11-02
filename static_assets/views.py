"""Various static assets views."""
import datetime
import json
import logging
import mimetypes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http import Http404
from django.http.request import HttpRequest
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
import requests

from common.storage import get_s3_url
from common.queries import has_active_subscription, is_free_static_asset
from static_assets.models.progress import UserVideoProgress
from static_assets.models import Video, VideoTrack, StaticAsset
from training.queries.progress import (
    set_video_progress,
    set_section_progress_started,
    set_section_progress_finished,
)
from static_assets.coconut import events
from stats.models import StaticAssetDownload

log = logging.getLogger(__name__)
# CloudFront does not support files larger than 20GB
CDN_SIZE_LIMIT_BYTES = 20 * 1024 ** 3


@require_POST
@login_required
def video_progress(request: HttpRequest, *, video_pk: int) -> JsonResponse:
    """Update video progress."""
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
    with requests.get(track.source.url) as storage_response:
        if storage_response.status_code != 200:
            raise Http404()
        original_mimetype, _ = mimetypes.guess_type(track.source.name)
        response = HttpResponse(storage_response.content, content_type=original_mimetype)
        return response


@require_GET
@login_required
def download_view(request, source: str):
    """Redirect to a storage URL of the given source file, if found in static assets."""
    static_asset = get_object_or_404(StaticAsset, source=source)
    can_dowload = has_active_subscription(request.user) or is_free_static_asset(static_asset.pk)
    if not can_dowload:
        raise Http404()

    download_source = static_asset.download_source
    StaticAssetDownload.create_from_request(request, static_asset.pk)
    redirect_url = (
        download_source.url
        if static_asset.size_bytes <= CDN_SIZE_LIMIT_BYTES
        else get_s3_url(download_source.name)
    )
    return redirect(redirect_url, permanent=False)
