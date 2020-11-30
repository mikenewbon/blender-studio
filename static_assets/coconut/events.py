# Collection of functions used when the coconut_webhook is called

import datetime
import logging
from urllib.parse import urlparse

from django.http.response import JsonResponse
from static_assets.models.static_assets import Video, VideoVariation
from static_assets.tasks import move_blob_from_upload_to_storage

log = logging.getLogger(__name__)


def source_transferred(job: dict, video: Video):
    """Handle a source.transferred event."""
    # Set related static asset properties (size and content_type)
    video.static_asset.size_bytes = job['metadata']['format']['size']
    video.static_asset.content_type = job['metadata']['format']['mime_type']
    video.static_asset.save()
    # Set Video properties
    video.duration = datetime.timedelta(seconds=job['metadata']['format']['duration'])
    video.height = job['metadata']['streams']['video']['height']
    video.width = job['metadata']['streams']['video']['width']
    video.save()


def output_processed_images(job: dict, video: Video):
    """Handle aa output.processed event for image files."""
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


def output_processed_video(job: dict, video: Video):
    """Handle aa output.processed event for a video file."""
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
