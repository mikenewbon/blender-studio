import datetime
import json
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from common.tests.factories.static_assets import VideoFactory
from common.tests.factories.training import SectionFactory
from static_assets.models import Video, VideoVariation
import static_assets.tasks

# Predefined values, used across the 3 webhook bodies below

SOURCE_VIDEO_DURATION_SEC = "13"
SOURCE_VIDEO_WIDTH = 1342
SOURCE_VIDEO_HEIGHT = 708
SOURCE_VIDEO_SIZE_BYTES = "1756160"
SOURCE_VIDEO_MEDIA_TYPE = "video/mp4"

VIDEO_THUMBNAIL_URLS = ["<url-to>/44460d5146b3feaacb22f3bf9902d7c5.thumbnail.jpg"]

PROCESSED_VIDEO_URL = "<url-to>/44460d5146b3feaacb22f3bf9902d7c5.720p.mp4"
PROCESSED_VIDEO_WIDTH = 1364
PROCESSED_VIDEO_HEIGHT = 720
PROCESSED_VIDEO_SIZE_BYTES = 1611776
PROCESSED_VIDEO_MEDIA_TYPE = "video/mp4"

WEBHOOK_TRANSFERRED = {
    "id": 68354025,
    "event": "source.transferred",
    "progress": "33%",
    "metadata": {
        "source": {
            "streams": [
                {
                    "index": 0,
                    "codec_name": "h264",
                    "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                    "profile": "High",
                    "codec_type": "video",
                    "codec_time_base": "1/48",
                    "codec_tag_string": "avc1",
                    "codec_tag": "0x31637661",
                    "width": SOURCE_VIDEO_WIDTH,
                    "height": SOURCE_VIDEO_HEIGHT,
                    "coded_width": 2048,
                    "coded_height": 864,
                    "has_b_frames": 2,
                    "sample_aspect_ratio": "1:1",
                    "display_aspect_ratio": "1024:429",
                    "pix_fmt": "yuv420p",
                    "level": 40,
                    "chroma_location": "left",
                    "refs": 1,
                    "is_avc": "true",
                    "nal_length_size": "4",
                    "r_frame_rate": "24/1",
                    "avg_frame_rate": "24/1",
                    "time_base": "1/12288",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "duration_ts": 35840,
                    "duration": "2.916667",
                    "bit_rate": "1627718",
                    "bits_per_raw_sample": "8",
                    "nb_frames": "70",
                    "disposition": {
                        "default": 1,
                        "dub": 0,
                        "original": 0,
                        "comment": 0,
                        "lyrics": 0,
                        "karaoke": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "visual_impaired": 0,
                        "clean_effects": 0,
                        "attached_pic": 0,
                        "timed_thumbnails": 0,
                    },
                    "tags": {"handler_name": "VideoHandler"},
                }
            ],
            "format": {
                "filename": "<coconut-temp-storage-location>",
                "nb_streams": 1,
                "nb_programs": 0,
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "format_long_name": "QuickTime / MOV",
                "start_time": "0.000000",
                "duration": SOURCE_VIDEO_DURATION_SEC,
                "size": SOURCE_VIDEO_SIZE_BYTES,
                "bit_rate": "1632181",
                "probe_score": 100,
                "tags": {
                    "major_brand": "qt  ",
                    "minor_version": "512",
                    "compatible_brands": "qt  ",
                    "date": "2020/11/30 18:55:15",
                    "encoder": "Lavf58.29.100",
                },
            },
        }
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
        "mp4:0x720": {
            "streams": [
                {
                    "index": 0,
                    "codec_name": "h264",
                    "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                    "profile": "Constrained Baseline",
                    "codec_type": "video",
                    "codec_time_base": "1/48",
                    "codec_tag_string": "avc1",
                    "codec_tag": "0x31637661",
                    "width": PROCESSED_VIDEO_WIDTH,
                    "height": PROCESSED_VIDEO_HEIGHT,
                    "coded_width": 2592,
                    "coded_height": 1088,
                    "has_b_frames": 0,
                    "sample_aspect_ratio": "26331:26332",
                    "display_aspect_ratio": "1024:429",
                    "pix_fmt": "yuv420p",
                    "level": 30,
                    "chroma_location": "left",
                    "refs": 1,
                    "is_avc": "true",
                    "nal_length_size": "4",
                    "r_frame_rate": "24/1",
                    "avg_frame_rate": "24/1",
                    "time_base": "1/12288",
                    "start_pts": 0,
                    "start_time": "0.000000",
                    "duration_ts": 35840,
                    "duration": "2.916667",
                    "bit_rate": "722095",
                    "bits_per_raw_sample": "8",
                    "nb_frames": "70",
                    "disposition": {
                        "default": 1,
                        "dub": 0,
                        "original": 0,
                        "comment": 0,
                        "lyrics": 0,
                        "karaoke": 0,
                        "forced": 0,
                        "hearing_impaired": 0,
                        "visual_impaired": 0,
                        "clean_effects": 0,
                        "attached_pic": 0,
                        "timed_thumbnails": 0,
                    },
                    "tags": {"language": "und", "handler_name": "VideoHandler"},
                }
            ],
            "format": {
                "filename": PROCESSED_VIDEO_URL,
                "nb_streams": 1,
                "nb_programs": 0,
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "format_long_name": "QuickTime / MOV",
                "start_time": "0.000000",
                "duration": SOURCE_VIDEO_DURATION_SEC,
                "size": PROCESSED_VIDEO_SIZE_BYTES,
                "bit_rate": "725188",
                "probe_score": 100,
                "tags": {
                    "major_brand": "isom",
                    "minor_version": "512",
                    "compatible_brands": "isomiso2avc1mp41",
                    "date": "2020/11/30 18:55:15",
                    "encoder": "Lavf58.29.100",
                },
            },
        }
    },
}

WEBHOOK_JOB_COMPLETED = {
    "id": 68126909,
    "errors": {},
    "output_urls": {"jpg:1280x": VIDEO_THUMBNAIL_URLS, "mp4:0x720": PROCESSED_VIDEO_URL},
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
        video.static_asset.original_filename = 'video.mp4'
        video.static_asset.thumbnail = ''
        video.static_asset.save()
        page_url = reverse('coconut-webhook', kwargs={'video_id': video.id})
        # Video was successfully uploaded to the processing platform
        response = self.client.post(
            page_url, json.dumps(WEBHOOK_TRANSFERRED), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        updated_video: Video = Video.objects.get(pk=video.id)
        self.assertEqual(updated_video.width, SOURCE_VIDEO_WIDTH)
        self.assertEqual(
            updated_video.duration, datetime.timedelta(seconds=float(SOURCE_VIDEO_DURATION_SEC))
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

    @patch('static_assets.tasks.s3_client')
    @patch(
        # Make sure background task is executed as a normal function
        'static_assets.coconut.events.move_blob_from_upload_to_storage',
        new=static_assets.tasks.move_blob_from_upload_to_storage.task_function,
    )
    def test_training_video_variation_file_has_content_disposition(self, mock_s3_client):
        video: Video = VideoFactory(
            static_asset__original_filename='video.mp4',
            static_asset__thumbnail='',
        )
        # Attach this video to a training section
        SectionFactory(
            name='001. Test training section.',
            static_asset=video.static_asset,
        )

        # Simulate a finished processing job
        page_url = reverse('coconut-webhook', kwargs={'video_id': video.id})
        response = self.client.post(
            page_url, json.dumps(WEBHOOK_VIDEO_PROCESSED), content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        # Check that appropriate calls to the storage has been made, with all the right metadata:
        mock_s3_client.copy_object.assert_called_once_with(
            Bucket='blender-studio-test',
            Key='<url-to>/44460d5146b3feaacb22f3bf9902d7c5.720p.mp4',
            CopySource={
                'Bucket': 'blender-studio-uploads',
                'Key': '<url-to>/44460d5146b3feaacb22f3bf9902d7c5.720p.mp4',
            },
            MetadataDirective='REPLACE',
            ContentType='video/mp4',
            ContentDisposition='attachment; filename="001-test-training-section-720p.mp4"',
        )
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket='blender-studio-uploads',
            Key='<url-to>/44460d5146b3feaacb22f3bf9902d7c5.720p.mp4',
        )
