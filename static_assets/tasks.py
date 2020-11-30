import logging
import pathlib
import boto3
import botocore.exceptions as botocore_exceptions

from background_task import background
from django.conf import settings
from django.urls import reverse

import static_assets.coconut.job
from static_assets.models import static_assets as models_static_assets


log = logging.getLogger(__name__)

s3_client = boto3.client(
    's3',
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

    # The jpg:1280x thumbnail
    outputs['jpg:1280x'] = f"{job_storage_base_out}{source_path.with_suffix('.thumbnail.jpg')}"

    # The mp4:1080p version of the path if the width is >= 1920px wide
    outputs[
        'mp4:0x1080'
    ] = f"{job_storage_base_out}{source_path.with_suffix('.1080p.mp4')}, if=$source_width >= 1920"

    # The mp4:720p version of the path if the width is < 1920px wide
    outputs[
        'mp4:0x720'
    ] = f"{job_storage_base_out}{source_path.with_suffix('.720p.mp4')}, if=$source_width < 1920"

    # Webhook for encoding updates
    job_webhook = reverse('coconut-webhook', kwargs={'video_id': static_asset.video.id})

    j = static_assets.coconut.job.create(
        api_key=settings.COCONUT_API_KEY,
        source=f'{static_asset.source.url}',
        webhook=f'{settings.COCONUT_DECLARED_HOSTNAME}{job_webhook}, events=true, metadata=true',
        outputs=outputs,
    )

    if j['status'] == 'ok':
        log.info('Started processing job %i' % j['id'])
    else:
        log.error('Error %s - %s' % (j['error_code'], j['message']))

@background()
def move_blob_from_upload_to_storage(key):
    """Move a blob from the upload bucket to the permanent location."""
    try:
        log.info(
            'Copying %s%s to %s'
            % (settings.AWS_UPLOADS_BUCKET_NAME, key, settings.AWS_STORAGE_BUCKET_NAME)
        )
        s3_client.copy_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            CopySource={'Bucket': settings.AWS_UPLOADS_BUCKET_NAME, 'Key': key},
            MetadataDirective="REPLACE",
        )
    except Exception as e:
        log.error('Generic exception on %s' % key)
        log.error(str(e))
        return

    log.debug('Deleting %s from upload bucket' % key)
    s3_client.delete_object(
        Bucket=settings.AWS_UPLOADS_BUCKET_NAME, Key=key,
    )
