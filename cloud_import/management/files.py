import boto3
import os
import requests
from google.cloud import storage
import pathlib
from typing import Optional
from django.conf import settings
from botocore.exceptions import ClientError


overwrite = False

dirname = os.path.dirname(__file__)
dirname_abspath = pathlib.Path(os.path.abspath(dirname)).parent
google_storage_client = storage.Client.from_service_account_json(
    dirname_abspath.parent / "studio" / "blender-cloud-credentials.json"
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def generate_s3_path(file_pah: str) -> str:
    file_path = pathlib.Path(file_pah)
    pure_stem = file_path.stem.split('-')[0]
    return str(pathlib.Path(pure_stem[:2], pure_stem, file_path.name))


def download_file_from_storage(
    file_doc, file_dir_path: pathlib.Path, variation_subdoc=None
) -> Optional[pathlib.Path]:
    """Fetch a file from storage and save it locally."""

    def download_blob_to_file(project, filepath, destination_filepath):
        """Download a blob from GCS.

        file_doc can be a file document or a variation subdocument
        """
        bucket = google_storage_client.get_bucket(str(project))
        blob = bucket.get_blob(f"_/{filepath}")
        if not blob:
            print(f"Blob {destination_filepath.name} does not exist")
            return None
        if blob and blob.exists():
            if not destination_filepath.exists() or overwrite:
                print(f"Downloading {destination_filepath.name}")
                blob.download_to_filename(str(destination_filepath))
            else:
                print(f"Blob {destination_filepath.name} already downloaded")
            return destination_filepath.name

    def download_static_to_file(url, destination_filepath):
        if destination_filepath.exists() and overwrite is False:
            print(f"File {destination_filepath.name} already downloaded")
            return
        print(f"Requesting {url}")
        r = requests.get(url, allow_redirects=True)
        open(destination_filepath, "wb").write(r.content)

    def download_to_file(
        file_doc, file_path, file_dir_path: pathlib.Path
    ) -> Optional[pathlib.Path]:
        destination_filepath = file_dir_path / pathlib.Path(file_path).name

        if file_doc["backend"] == "gcs":
            if download_blob_to_file(file_doc["project"], file_path, destination_filepath):
                return destination_filepath
            else:
                return None
        elif file_doc["backend"] == "pillar":
            download_static_to_file(file_doc["link"], destination_filepath)
            return destination_filepath
        else:
            print(f"[WARNING]: Backend {file_doc['backend']} is not supported")
            return

    print(f"\tFetching {file_doc['_id']} {file_doc['name']}")
    file_path = file_doc['file_path'] if not variation_subdoc else variation_subdoc['file_path']
    return download_to_file(file_doc, file_path, file_dir_path)

    # if "video" in file_doc["content_type"] and "variations" in file_doc:
    #     for v in file_doc["variations"]:
    #         download_to_file(file_doc, v["file_path"], file_dir_path)


def file_on_s3(s3_client, bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        return int(e.response['Error']['Code']) != 404
    return True


def upload_file_to_s3(source_path: str, dest_path: str, **kwargs):
    def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
        """Returns a human readable string representation of bytes"""
        return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])

    with open(source_path, "rb") as f:
        human_size_str = human_size(pathlib.Path(source_path).stat().st_size)
        print(f"Uploading {human_size_str} {dest_path} to S3 {settings.AWS_STORAGE_BUCKET_NAME}")
        extra_args = settings.AWS_S3_OBJECT_PARAMETERS.copy()
        extra_args.update(**{k: v for k, v in kwargs.items() if v is not None})
        s3_client.upload_fileobj(
            f, settings.AWS_STORAGE_BUCKET_NAME, dest_path, ExtraArgs=extra_args
        )
