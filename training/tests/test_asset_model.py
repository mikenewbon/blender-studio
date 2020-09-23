from django.test import TestCase
from unittest.mock import patch

from common.tests.factories.training import AssetFactory
from training.models import Asset


class TestAssetModel(TestCase):
    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_asset_storage_urls(self, mock_storage_url):
        """Tests for the training Asset file fields.

        Create a new asset and check that the right storage is called when its file URLs are accessed.
        """
        asset: Asset = AssetFactory()

        self.assertEqual(asset.file.url, 's3://file')

        mock_storage_url.assert_called_once_with(asset.file.name)
