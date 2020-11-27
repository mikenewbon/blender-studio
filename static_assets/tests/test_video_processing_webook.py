import datetime
import json
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, call

from background_task.models import Task
from common.tests.factories.static_assets import StaticAssetFactory, VideoFactory
from static_assets.models import StaticAsset, Video, VideoVariation

# Predefined values, used across the 3 webhook bodies below

SOURCE_VIDEO_DURATION_SEC = 13
SOURCE_VIDEO_WIDTH = 1342
SOURCE_VIDEO_HEIGHT = 708
SOURCE_VIDEO_SIZE_BYTES = 1756160
SOURCE_VIDEO_MEDIA_TYPE = "video/mp4"

VIDEO_THUMBNAIL_URLS = ["<url-to>/44460d5146b3feaacb22f3bf9902d7c5.thumbnail.jpg"]

PROCESSED_VIDEO_URL = "<url-to>/44460d5146b3feaacb22f3bf9902d7c5.720p.mp4"
PROCESSED_VIDEO_WIDTH = 1364
PROCESSED_VIDEO_HEIGHT = 720
PROCESSED_VIDEO_SIZE_BYTES = 1611776
PROCESSED_VIDEO_MEDIA_TYPE = "video/mp4"

WEBHOOK_TRANSFERRED = {
    "id": 68126909,
    "event": "source.transferred",
    "progress": "33%",
    "metadata": {
        "streams": {
            "video": {
                "codec": "h264",
                "width": SOURCE_VIDEO_WIDTH,
                "height": SOURCE_VIDEO_HEIGHT,
                "aspect": 1.895480226,
                "pix_fmt": "yuv420p",
                "fps": 30,
                "bitrate": 1034,
                "rotation": 0,
            }
        },
        "format": {
            "name": "mov",
            "duration": SOURCE_VIDEO_DURATION_SEC,
            "size": SOURCE_VIDEO_SIZE_BYTES,
            "mime_type": SOURCE_VIDEO_MEDIA_TYPE,
        },
    },
}

WEBHOOK_THUMBNAIL_PROCESSED = {
    "id": 68126909,
    "event": "output.processed",
    "progress": "66%",
    "format": "jpg:1280x",
    "urls": VIDEO_THUMBNAIL_URLS,
}

WEBHOOK_VIDEO_PROCESSED = {
    "id": 68126909,
    "event": "output.processed",
    "progress": "100%",
    "format": "mp4:0x720",
    "url": PROCESSED_VIDEO_URL,
    "metadata": {
        "streams": {
            "video": {
                "codec": "h264",
                "width": PROCESSED_VIDEO_WIDTH,
                "height": PROCESSED_VIDEO_HEIGHT,
                "aspect": 1.8944444444,
                "pix_fmt": "yuv420p",
                "fps": 30,
                "bitrate": 949,
                "rotation": 0,
            }
        },
        "format": {
            "name": "mov",
            "duration": SOURCE_VIDEO_DURATION_SEC,
            "size": PROCESSED_VIDEO_SIZE_BYTES,
            "mime_type": PROCESSED_VIDEO_MEDIA_TYPE,
        },
    },
}

WEBHOOK_JOB_COMPLETED = {
    "id": 68126909,
    "errors": {},
    "output_urls": {"jpg:1280x": VIDEO_THUMBNAIL_URLS, "mp4:0x720": PROCESSED_VIDEO_URL,},
    "event": "job.completed",
}


class TestVideoProcessingWebhook(TestCase):
    @patch('storages.backends.s3boto3.S3Boto3Storage.url', return_value='s3://file')
    def test_coconut_webhook(self, mock_storage_url):
        """Send a series of POST request to the video processing endpoint.

        This emulates what is expected during a video processing job:
        - the source file is uploaded to the processing platform
        - a thumbnail is generated
        - a video variation is encoded
        - the job is marked as completed
        """
        video: Video = VideoFactory()
        page_url = reverse('coconut-webhook', kwargs={'video_id': video.id})
        # Video was successfully uploaded to the processing platform
        response = self.client.post(
            page_url, json.dumps(WEBHOOK_TRANSFERRED), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        updated_video: Video = Video.objects.get(pk=video.id)
        self.assertEqual(updated_video.width, SOURCE_VIDEO_WIDTH)
        self.assertEqual(
            updated_video.duration, datetime.timedelta(seconds=SOURCE_VIDEO_DURATION_SEC)
        )
        self.assertEqual(updated_video.static_asset.content_type, SOURCE_VIDEO_MEDIA_TYPE)

        # Thumbnail was created
        response = self.client.post(
            page_url, json.dumps(WEBHOOK_THUMBNAIL_PROCESSED), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        updated_video: Video = Video.objects.get(pk=video.id)
        self.assertEqual(updated_video.static_asset.thumbnail, VIDEO_THUMBNAIL_URLS[0])

        # Video was encoded
        response = self.client.post(
            page_url, json.dumps(WEBHOOK_VIDEO_PROCESSED), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        updated_video: Video = Video.objects.get(pk=video.id)
        video_variation: VideoVariation = VideoVariation.objects.get(video=updated_video)
        self.assertEqual(video_variation.source, PROCESSED_VIDEO_URL)
        self.assertEqual(video_variation.resolution_label, '720p')
        self.assertEqual(len(updated_video.variations.all()), 1)

        # Job was completed
        response = self.client.post(
            page_url, json.dumps(WEBHOOK_JOB_COMPLETED), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
