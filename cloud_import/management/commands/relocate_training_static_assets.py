"""This command is only for reference
(was used once during 9f0c72aed39030deaca2f52fb159efe1e58fb9ec)
"""
import datetime

import training.models as models_training
import static_assets.models as models_static_assets
from cloud_import.management.mixins import ImportCommand


class Command(ImportCommand):
    help = 'Relocate training data'

    def relocate_videos(self):
        for video in models_training.sections.Video.objects.all():
            try:
                self.console_log(f"Attempting to relocate {video.file}")
                static_asset_base = models_static_assets.StaticAsset.objects.get(source=video.file)
            except models_static_assets.StaticAsset.DoesNotExist:
                self.console_log(f"Does not exist {video.id}")
                static_asset_base = models_static_assets.StaticAsset.objects.create(
                    source=video.file,
                    source_type='video',
                    original_filename='',
                    size_bytes=10,
                    user_id=1,
                )

            try:
                models_static_assets.Video.objects.get(static_asset=static_asset_base)
            except models_static_assets.Video.DoesNotExist:
                models_static_assets.Video.objects.create(
                    static_asset=static_asset_base, duration=datetime.timedelta(minutes=1)
                )

            if not video.section.static_asset:
                video.section.static_asset = static_asset_base
                video.section.save()

    def relocate_assets(self):
        for asset in models_training.sections.Asset.objects.all():
            try:
                self.console_log(f"Attempting to relocate {asset.file}")
                static_asset_base = models_static_assets.StaticAsset.objects.get(source=asset.file)
            except models_static_assets.StaticAsset.DoesNotExist:
                self.console_log(f"Creating asset {asset.id}")
                static_asset_base = models_static_assets.StaticAsset.objects.create(
                    source=asset.file,
                    source_type='file',
                    original_filename='',
                    size_bytes=10,
                    user_id=1,
                )
            if not asset.section.static_asset:
                asset.section.static_asset = static_asset_base
                asset.section.save()

    def handle(self, *args, **options):
        self.relocate_videos()
        self.relocate_assets()
