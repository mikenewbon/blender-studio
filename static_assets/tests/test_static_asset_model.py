import datetime
from django.test import TestCase
from unittest.mock import patch, call

from common.tests.factories.static_assets import StaticAssetFactory, VideoFactory
from static_assets.models import StaticAsset, Video


class TestStaticAssetModel(TestCase):
    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_static_asset_storage_urls(self, mock_storage_url):
        """Tests for the StaticAsset file fields.

        Create a new static asset and check that the right storage is called when its file URLs are accessed.
        """
        asset: StaticAsset = StaticAssetFactory()

        self.assertEqual(asset.source.url, 's3://file')
        self.assertEqual(asset.thumbnail.url, 's3://file')

        mock_storage_url.assert_has_calls((call(asset.source.name,), call(asset.thumbnail.name,),))

    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_video_duration_label(self, mock_storage_url):

        video: Video = VideoFactory()

        video.duration = datetime.timedelta(seconds=10)
        self.assertEqual(video.duration_label, '0:10')

        video.duration = datetime.timedelta(minutes=1, seconds=10)
        self.assertEqual(video.duration_label, '1:10')

        video.duration = datetime.timedelta(minutes=10, seconds=10)
        self.assertEqual(video.duration_label, '10:10')

        video.duration = datetime.timedelta(hours=1, minutes=10, seconds=1)
        self.assertEqual(video.duration_label, '1:10:01')

        video.duration = datetime.timedelta(hours=1, minutes=1, seconds=1)
        self.assertEqual(video.duration_label, '1:01:01')
