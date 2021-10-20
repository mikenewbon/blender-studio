"""One-time helper for fixing training videos metadata on S3."""
from pathlib import PurePosixPath
import logging
import mimetypes

from django.conf import settings
from django.core.management.base import BaseCommand

import boto3
import botocore
from static_assets.models import StaticAsset, Video

logger = logging.getLogger(__name__)
logger.propagate = False
formatter = logging.Formatter('%(asctime)s %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.handlers = []
logger.addHandler(ch)
logger.setLevel(logging.DEBUG)
CONTENT_TYPE_ALLOW_OVERWRITE = (
    # (possibly incorrect, corrected based on the extension of the stored file),
    ('application/PNG', 'image/png'),
    ('application/blend', 'application/x-blender'),
    ('application/gif', 'image/gif'),
    ('application/octet-stream', 'application/x-blender'),
    ('application/octet-stream', 'application/x-krita'),
    ('application/octet-stream', 'model/obj'),
    ('application/sla', 'model/stl'),
    ('application/svg', 'image/svg+xml'),
    ('application/txt', 'text/plain'),
    ('application/x-mp4', 'video/mp4'),
    ('image/jpg', 'image/jpeg'),
    ('video/avi', 'video/x-msvideo'),
    ('video/m4v', 'video/mp4'),
    ('video/mov', 'video/mp4'),
    ('video/mov', 'video/quicktime'),
    ('video/mp4', 'video/webm'),
    ('video/quicktime', 'video/mp4'),
    ('image/png', 'image/jpeg'),
)
CONTENT_TYPE_IGNORE = (
    ('application/octet-stream', None),
    ('image/jpeg', None),
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
s3 = boto3.resource(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)
BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME


def _get_s3_object(key):
    # check if this key already exists in S3
    try:
        obj = s3.Object(BUCKET_NAME, key)
        obj.content_type
        return obj
    except botocore.exceptions.ClientError as e:
        logger.error('%s: %s', key, e.response)
        if e.response['Error']['Code'] != "404":
            raise


class Command(BaseCommand):
    """See below."""

    help = 'Fix Content headers on existing trainings to make them downloadable.'

    def _handle_static_asset_source(self, source, content_type, content_disposition):
        if not source:
            # logger.error('No source file: %s, nothing to do', source)
            return
        _path = source.name
        if not PurePosixPath(_path).suffix:
            logger.warning('%s has no extension, skipping', _path)
            return
        original_mimetype, _ = mimetypes.guess_type(_path)
        if not content_type and not original_mimetype:
            logger.warning('%s unable to determine MIME-type, skipping', _path)
            return
        if (content_type, original_mimetype) in CONTENT_TYPE_IGNORE:
            logger.warning(
                '%s ignoring (%s, %s) content_type', _path, content_type, original_mimetype
            )
            return
        assert (
            content_type == original_mimetype
        ), f'Wrong stored content type: {content_type} != {original_mimetype} of {_path}'
        _file = _get_s3_object(_path)
        if not _file:
            logger.warning('Missing file %s', _path)
            return
        old_metadata = {
            'ContentType': _file.content_type,
            'CacheControl': _file.cache_control,
            'ContentDisposition': _file.content_disposition,
        }
        metadata = {
            'ContentType': content_type,
            'CacheControl': settings.AWS_S3_OBJECT_PARAMETERS['CacheControl'],
            'ContentDisposition': content_disposition or _file.content_disposition,
        }
        if old_metadata['ContentType'] != metadata['ContentType']:
            self.wrong_content_type += 1
        if old_metadata['ContentDisposition'] != metadata['ContentDisposition']:
            self.wrong_disposition += 1
        if old_metadata['CacheControl'] != metadata['CacheControl']:
            self.wrong_cache_control += 1
        if old_metadata != metadata:
            logger.warning(f'{_file.key} replacing metadata: {old_metadata} -> {metadata}')
            if not self.is_dry_run:
                try:
                    _file.copy_from(
                        CopySource={
                            'Bucket': BUCKET_NAME,
                            'Key': _file.key,
                        },
                        # N.B.: REPLACE is the only way to update metadata, apparently.
                        # This will create a new version of the key in a *versioned* bucket,
                        # or just overwrite the key in a non-versioned one.
                        # Make sure to set ALL the metadata key has to have, because it's replaced
                        MetadataDirective='REPLACE',
                        **metadata,
                    )
                except botocore.exceptions.ClientError as e:
                    logger.error('%s: %s', _path, e.response)
                    if 'the maximum allowable size for a copy source' not in str(e):
                        raise

    def _handle_video(self, video: Video):
        variations = video.variations.all()
        self._handle_static_asset_source(
            video.static_asset.source, video.static_asset.content_type, video.content_disposition
        )
        for var in variations:
            self._handle_static_asset_source(var.source, var.content_type, var.content_disposition)

    def _handle_other_static_asset(self, static_asset: StaticAsset):
        self._handle_static_asset_source(
            static_asset.source, static_asset.content_type, static_asset.content_disposition
        )

    def _fix_content_type(self, static_asset: StaticAsset):
        content_type, _ = mimetypes.guess_type(static_asset.source.name)
        if content_type and (
            not static_asset.content_type
            or (static_asset.content_type, content_type) in CONTENT_TYPE_ALLOW_OVERWRITE
        ):
            logger.warning(
                '%s updating .content_type "%s" -> "%s"',
                static_asset.source.name,
                static_asset.content_type,
                content_type,
            )
            static_asset.content_type = content_type
            self.to_update.append(static_asset)

    @property
    def is_dry_run(self) -> bool:
        """Return True if command was called with in dry run mode."""
        return self.options['dry_run']

    def add_arguments(self, parser):
        """Add custom arguments to the command."""
        parser.add_argument('--dry-run', dest='dry_run', action='store_true')
        parser.add_argument('--no-dry-run', dest='dry_run', action='store_false')
        parser.set_defaults(dry_run=True)
        parser.add_argument('--id-min', type=int, default=0)

    def handle(self, *args, **options):  # noqa: D102
        """Do what is described in help."""
        self.options = options
        logger.warning('Dry run: %s', self.is_dry_run)

        mimetypes.add_type('application/x-blender', '.blend')
        mimetypes.add_type('application/x-radiance-hdr', '.hdr')
        mimetypes.add_type('application/x-exr', '.exr')

        self.wrong_content_type, self.wrong_disposition, self.wrong_cache_control = 0, 0, 0
        self.to_update = []
        # for s in StaticAsset.objects.filter(
        #   source='86/86eeba31b4008e82a2f4e78437ca504709128e8d/86eeba31b4008e82a2f4e78437ca504709128e8d.m4v'
        # ):
        for s in StaticAsset.objects.filter(id__gte=self.options['id_min']).order_by('id'):
            self._fix_content_type(s)
            if getattr(s, 'video', None):
                self._handle_video(s.video)
            else:
                self._handle_other_static_asset(s)
        if self.to_update:
            logger.warning(f'content_type not set on {len(self.to_update)} static assets')
            if not self.is_dry_run:
                StaticAsset.objects.bulk_update(
                    # date_updated is included to avoid auto-update of it
                    self.to_update,
                    fields={'content_type', 'date_updated'},
                    batch_size=300,
                )
        if self.wrong_content_type:
            logger.warning(f'Wrong Content-Type: {self.wrong_content_type}')
        if self.wrong_disposition:
            logger.warning(f'Wrong Content-Disposition: {self.wrong_disposition}')
        if self.wrong_cache_control:
            logger.warning(f'Wrong Cache-Control: {self.wrong_cache_control}')
