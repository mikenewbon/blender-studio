# noqa: D100
import datetime
import mimetypes
import os
import os.path
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from cloud_import.management import files
from common.upload_paths import get_upload_to_hashed_path
from films.models import Film, Asset, Collection
from static_assets.models import StaticAsset


def _upload(file_path: str, dest_file_path_s3: str, static_asset: StaticAsset) -> str:
    print(file_path, dest_file_path_s3)
    # Check if file is already on S3
    if files.file_on_s3(
        files.s3_client,
        settings.AWS_STORAGE_BUCKET_NAME,
        dest_file_path_s3,
    ):
        print(f"File {dest_file_path_s3} already exists on S3, skipping upload")
        return dest_file_path_s3

    guessed_content_type, _ = mimetypes.guess_type(dest_file_path_s3)
    content_type = getattr(static_asset, 'content_type', None) or guessed_content_type
    content_disposition = getattr(static_asset, 'content_disposition', None)
    print(content_type, content_disposition, guessed_content_type)
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
    """Upload Sprite Fright takes."""

    help = 'Upload Sprite Fright takes'
    source_path = '/render/sprites/export_public'
    collection_slug = '3921c918116910'
    sf_takes_paths_file = 'sf_takes_paths.csv'

    def handle(self, *args, **options):  # noqa: D102
        film = Film.objects.get(title='Sprite Fright')
        collection, is_new = Collection.objects.get_or_create(
            film=film,
            slug=self.collection_slug,
        )
        user = film.filmcrew_set.filter(role='Pipeline TD').get().user
        sf_takes_paths = {}
        if os.path.isfile(self.sf_takes_paths_file):
            with open(self.sf_takes_paths_file) as f:
                sf_takes_paths = {
                    li.strip().split(',')[0]: li.strip().split(',')[1:] for li in f.readlines()
                }
        # for name in os.listdir(self.source_path):
        for name in sf_takes_paths:
            # if os.path.isdir(name) or name.startswith('.'):
            #    continue
            file_path = os.path.join(self.source_path, name)
            _, _, version, year, month, day, ext = re.split(r'[-_.]', name)
            year, month, day = map(int, (year, month, day))
            date = make_aware(datetime.datetime(year, month, day))
            original_filename = (
                name.replace('sf-edit', 'SpriteFright')
                .replace('_', '-')
                .replace(f'{year}-{month}-{day}', f'{year}-{month:02d}-{day:02d}')
            )
            size_bytes = (
                sf_takes_paths[name][1] if name in sf_takes_paths else os.path.getsize(file_path)
            )
            static_asset, is_new = StaticAsset.objects.get_or_create(
                original_filename=original_filename,
                source_type='video',
                user=user,
                size_bytes=size_bytes,
            )
            if not static_asset.source:
                if name in sf_takes_paths:
                    static_asset.source = sf_takes_paths[name][0]
                else:
                    static_asset.source = str(get_upload_to_hashed_path(None, name))
            dest_file_path_s3 = str(static_asset.source)
            sf_takes_paths[name] = (dest_file_path_s3, size_bytes)
            print(original_filename, name, version, dest_file_path_s3)
            _upload(file_path, dest_file_path_s3, static_asset)

            static_asset.contributors.set([u for u in film.crew.all() if u.pk != user.pk])
            static_asset.content_type, _ = mimetypes.guess_type(dest_file_path_s3)
            static_asset.save()

            film_asset, _ = Asset.objects.get_or_create(
                static_asset=static_asset,
                film=film,
                collection=collection,
            )
            film_asset.name = f'{film.title} - {version}'
            film_asset.is_spoiler = True
            film_asset.is_published = False
            film_asset.date_created = date
            film_asset.date_updated = date
            film_asset.date_published = date
            film_asset.category = 'production_file'
            film_asset.save()

            # Override dates
            static_asset.date_created = date
            static_asset.date_updated = date
            static_asset.save(update_fields={'date_created', 'date_updated'})
            film_asset.date_created = date
            film_asset.date_updated = date
            film_asset.date_published = date
            film_asset.save(update_fields={'date_created', 'date_updated', 'date_published'})

        with open(self.sf_takes_paths_file, 'w+') as f:
            for name, (dest_path, size_bytes) in sf_takes_paths.items():
                f.write(','.join((name, dest_path, str(size_bytes))) + '\n')
