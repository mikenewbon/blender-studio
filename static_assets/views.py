import datetime
import json
import logging
import pathlib
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, SuspiciousOperation
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from static_assets.models.progress import UserVideoProgress
from static_assets.models import Video, VideoVariation
from static_assets.tasks import move_blob_from_upload_to_storage
from training.queries.progress import (
    set_video_progress,
    set_section_progress_started,
    set_section_progress_finished,
)

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
    log.info('Updating video %i processing status to %s' % (video_id, job['event']))
    # On source.transferred
    if job['event'] == 'source.transferred':
        # Set related static asset properties (size and content_type)
        video.static_asset.size_bytes = job['metadata']['format']['size']
        video.static_asset.content_type = job['metadata']['format']['mime_type']
        video.static_asset.save()
        # Set Video properties
        video.duration = datetime.timedelta(seconds=job['metadata']['format']['duration'])
        video.height = job['metadata']['streams']['video']['height']
        video.width = job['metadata']['streams']['video']['width']
        video.save()
    # On output.processed (thumbnail)
    elif job['event'] == 'output.processed' and job['format'] == 'jpg:1280x':
        # Images urls are provided in a list, because the 'image' format allows
        # for the possibility of specifying more than one image.
        # The current implementation of video processing expects there to be only
        # one image, used as thumbnails. For this reason we get the first element
        # of the 'urls' list.
        if video.static_asset.thumbnail:
            log.debug('Video %i already has a thumbnail, not updating' % video.id)
            return JsonResponse({'status': 'ok'})
        source_path = urlparse(job['urls'][0]).path.strip('/')
        video.static_asset.thumbnail = source_path
        video.static_asset.save()
        move_blob_from_upload_to_storage(source_path)
    # On output.processed (video variation)
    elif job['event'] == 'output.processed' and 'mp4' in job['format']:
        # If a video variation is found, simply return. Otherwise, create one.
        source_path = urlparse(job['url']).path.strip('/')
        if VideoVariation.objects.filter(video=video, source=source_path).exists():
            log.debug('Video variation for video %i already exists' % video.id)
            return JsonResponse({'status': 'ok'})

        log.debug('Creating video variation for video %i' % video.id)

        def get_resolution_label(height: int):
            if height >= 1080:
                return '1080p'
            elif height >= 720:
                return '720p'
            elif height >= 540:
                return '540p'
            else:
                return ''

        video_variation = VideoVariation.objects.create(
            video=video,
            source=source_path,
            height=job['metadata']['streams']['video']['height'],
            width=job['metadata']['streams']['video']['width'],
            resolution_label=get_resolution_label(job['metadata']['streams']['video']['height']),
            size_bytes=job['metadata']['format']['size'],
            content_type=job['metadata']['format']['mime_type'],
        )
        video.variations.add(video_variation)
        log.debug('Created variation for video %i' % video.id)
        # Move the encoded video to the final location
        move_blob_from_upload_to_storage(source_path)
    # On job.completed (unused for now)
    elif job['event'] == 'job.completed':
        # TODO: Add publishing logic
        pass
    return JsonResponse({'status': 'ok'})
