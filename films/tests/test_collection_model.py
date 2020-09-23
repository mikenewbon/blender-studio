from django.test import TestCase
from unittest.mock import patch

from common.tests.factories.films import CollectionFactory
from films.models import Collection


class TestCollectionModel(TestCase):
    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_collection_storage_urls(self, mock_storage_url):
        """Tests for the Collection file fields.

        Create a new collection and check that the right storage is called when its file URLs are accessed.
        """
        collection: Collection = CollectionFactory()

        self.assertEqual(collection.thumbnail.url, 's3://file')

        mock_storage_url.assert_called_once_with(collection.thumbnail.name)
