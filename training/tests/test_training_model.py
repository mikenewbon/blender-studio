from django.test import TestCase
from unittest.mock import patch, call

from common.tests.factories.training import TrainingFactory
from training.models import Training


class TestTrainingModel(TestCase):
    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_training_storage_urls(self, mock_storage_url):
        """Tests for the Training file fields.

        Create a new training and check that the right storage is called when its file URLs are accessed.
        """
        training: Training = TrainingFactory()

        self.assertEqual(training.picture_header.url, 's3://file')
        self.assertEqual(training.thumbnail.url, 's3://file')

        mock_storage_url.assert_has_calls(
            (call(training.picture_header.name), call(training.thumbnail.name))
        )
