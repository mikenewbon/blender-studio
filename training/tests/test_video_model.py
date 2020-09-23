from django.test import TestCase
from unittest.mock import patch

from common.tests.factories.training import VideoFactory
from training.models import Video


class TestVideoModel(TestCase):
    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_video_storage_urls(self, mock_storage_url):
        """Tests for the training Video file fields.

        Create a new video and check that the right storage is called when its file URLs are accessed.
        """
        video: Video = VideoFactory()

        self.assertEqual(video.file.url, 's3://file')

        mock_storage_url.assert_called_once_with(video.file.name)
