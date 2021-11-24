# noqa: D100
import mimetypes
import os
import os.path
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from cloud_import.management import files
from common.upload_paths import get_upload_to_hashed_path


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _upload(file_path: str, dest_file_path_s3: str) -> str:
    print(file_path, dest_file_path_s3)
    # Check if file is already on S3
    if files.file_on_s3(
        files.s3_client,
        settings.AWS_STORAGE_BUCKET_NAME,
        dest_file_path_s3,
    ):
        print(f"File {dest_file_path_s3} already exists on S3, skipping upload")
        return dest_file_path_s3

    content_type, _ = mimetypes.guess_type(dest_file_path_s3)
    file_name = os.path.basename(file_path)
    content_disposition = f'attachment; filename="{file_name}"'
    print(content_type, content_disposition, content_type)
    assert content_type

    # Upload to S3
    files.upload_file_to_s3(
        str(file_path),
        dest_file_path_s3,
        ContentType=content_type,
        ContentDisposition=content_disposition,
    )
    return dest_file_path_s3


class Command(BaseCommand):
    """Upload a [large] file directly to S3."""

    help = 'Upload a [large] file directly to S3.'

    def add_arguments(self, parser):
        """Add list of files to command options."""
        parser.add_argument('files', nargs='+', type=str)

    def handle(self, *args, **options):  # noqa: D102
        for file_path in options['files']:
            if not os.path.isfile(file_path):
                raise
            file_name = os.path.basename(file_path)
            path = get_upload_to_hashed_path(None, file_name)
            dest_file_path_s3 = str(path)

            _upload(file_path, dest_file_path_s3)
