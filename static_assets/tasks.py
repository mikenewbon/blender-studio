"""Background processing of assets."""
import logging
import mimetypes
import pathlib
import time

from background_task import background
from django.conf import settings
from django.urls import reverse
import boto3

import static_assets.coconut.job
from common.upload_paths import get_upload_to_hashed_path
from static_assets.models import static_assets as models_static_assets


log = logging.getLogger(__name__)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
transcribe_client = boto3.client(
    'transcribe',
    region_name='eu-central-1',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


@background()
def create_video_processing_job(static_asset_id: int):
    """Create a video processing job.

    Because of the @background decorator, we only accept hashable
    arguments.

    This method relies on the Coconut video encoding service, which
    needs an API key in order to be used. A self-hosted, ffmpeg-based
    solution to provide a similar service can be implemented when
    needed.

    The video versions processing job delivers the following:
    - a 1080p or 720p (depending on the initial res), h264 with mp4 container
    - a 1280px wide jpeg thumbnail

    As part of the job creation we specify a webhook that will be used
    by the video processing service to post updates, triggering further
    operations.
    """
    if not settings.COCONUT_API_KEY:
        log.info('Missing COCONUT_API_KEY: no video encoding will be performed')
        return

    # The base S3 path, with credentials
    # TODO(fsiddi) look into replacing this with signed urls
    job_storage_base_out = (
        f"s3://{settings.AWS_ACCESS_KEY_ID}:{settings.AWS_SECRET_ACCESS_KEY}@"
        f"{settings.AWS_UPLOADS_BUCKET_NAME}/"
    )

    # Outputs
    outputs = {}

    static_asset = models_static_assets.StaticAsset.objects.get(pk=static_asset_id)
    source_path = pathlib.PurePath(static_asset.source.name)
    # keep original bitrates
    keep_parameters = 'keep=video_bitrate,audio_bitrate'

    # The jpg:1280x thumbnail
    outputs['jpg:1280x'] = f"{job_storage_base_out}{source_path.with_suffix('.thumbnail.jpg')}"

    # The mp4:1080p version of the path if the width is >= 1920px wide
    # 0x instead of *p to keep the original aspect ratio
    outputs['mp4:0x1080'] = (
        f"{job_storage_base_out}{source_path.with_suffix('.1080p.mp4')}, {keep_parameters},"
        " if=$source_width >= 1920"
    )

    # The mp4:720p version of the path if the width is < 1920px wide
    outputs['mp4:0x720'] = (
        f"{job_storage_base_out}{source_path.with_suffix('.720p.mp4')}, {keep_parameters},"
        " if=$source_width < 1920"
    )

    # Webhook for encoding updates
    job_webhook = reverse('coconut-webhook', kwargs={'video_id': static_asset.video.id})

    j = static_assets.coconut.job.create(
        api_key=settings.COCONUT_API_KEY,
        source=f'{static_asset.source.url}',
        webhook=f'{settings.COCONUT_DECLARED_HOSTNAME}{job_webhook}, events=true, metadata=true',
        outputs=outputs,
    )

    if j['status'] == 'processing':
        log.info('Started processing job %i' % j['id'])
    else:
        log.error('Error processing job %i' % (j['id']))


@background()
def move_blob_from_upload_to_storage(key, **metadata):
    """Move a blob from the upload bucket to the permanent location."""
    try:
        content_type, _ = mimetypes.guess_type(key)
        log.info(
            'Copying %s%s to %s, Content-Type: %s, additional metadata: %s',
            settings.AWS_UPLOADS_BUCKET_NAME,
            key,
            settings.AWS_STORAGE_BUCKET_NAME,
            content_type,
            metadata,
        )
        s3_client.copy_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            CopySource={'Bucket': settings.AWS_UPLOADS_BUCKET_NAME, 'Key': key},
            MetadataDirective='REPLACE',
            ContentType=content_type,
            **metadata,
        )
    except Exception as e:
        log.error('Generic exception on %s' % key)
        log.error(str(e))
        return

    log.debug('Deleting %s from upload bucket' % key)
    s3_client.delete_object(
        Bucket=settings.AWS_UPLOADS_BUCKET_NAME,
        Key=key,
    )


# @background() FIXME(anna): make a background job before merging
def create_video_transcribing_job(static_asset_id: int):
    """Create a video transcribing job."""
    static_asset = models_static_assets.StaticAsset.objects.get(pk=static_asset_id)
    job_uri = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{static_asset.video.source.name}"
    language = 'en-US'
    track, is_new = models_static_assets.VideoTrack.objects.get_or_create(
        video=static_asset.video, language=language
    )
    if not track.source.name:
        filename = 'transcription.vtt'
        output_path = get_upload_to_hashed_path(track, filename)
        track.source.name = str(output_path)
        track.save()
    else:
        output_path = pathlib.PurePath(track.source.name)
    # The job name must be unique, but we want to reuse the storage paths
    job_suffix = str(int(time.time() * 1000))
    job_name = output_path.parts[-1].split('.')[0] + f'-{job_suffix}'
    output_key = str(output_path).replace('.vtt', '.json')
    print(job_uri, job_name, job_suffix)
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        OutputKey=output_key,
        OutputBucketName=settings.AWS_STORAGE_BUCKET_NAME,
        MediaFormat=job_uri.split('.')[-1],
        LanguageCode=track.language,
        Subtitles={'Formats': ['vtt']},
    )
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("Not ready yet...")
        time.sleep(5)
    print(status)
