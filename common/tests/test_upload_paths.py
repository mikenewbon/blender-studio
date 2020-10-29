from django.test.testcases import TestCase
from pathlib import PosixPath
from unittest.mock import patch

from common.upload_paths import generate_hash_from_filename, get_upload_to_hashed_path


class TestUploadPaths(TestCase):
    @patch('common.upload_paths.uuid.uuid4', return_value='e8b542ae-97fc-4a3b-bae7-578f330945ba')
    def test_generate_hash_from_filename(self, _):
        self.assertEqual(
            generate_hash_from_filename('awesome-123.mov'), '60aaaae7629fdb4d40621e677c029cc0'
        )

    @patch('common.upload_paths.uuid.uuid4', return_value='e8b542ae-97fc-4a3b-bae7-578f330945ba')
    def test_get_upload_to_hashed_path(self, _):
        self.assertEqual(
            get_upload_to_hashed_path(None, 'awesome-123.mov'),
            PosixPath('60/60aaaae7629fdb4d40621e677c029cc0/60aaaae7629fdb4d40621e677c029cc0.mov'),
        )

    def test_get_upload_to_hashed_path_called_multiple_times_generates_different_paths(self):
        self.assertNotEqual(
            str(get_upload_to_hashed_path(None, 'awesome-123.mov')),
            str(get_upload_to_hashed_path(None, 'awesome-123.mov')),
        )
        self.assertNotEqual(
            str(get_upload_to_hashed_path(None, 'foobar 123.mov')),
            str(get_upload_to_hashed_path(None, 'adfassadfa-123.mp4')),
        )

    def test_get_upload_to_hashed_path_called_multiple_times_does_not_generate_ad_prefix(self):
        self.assertFalse(
            str(get_upload_to_hashed_path(None, 'awesome-123.mov')).startswith('ad'),
        )
        self.assertFalse(
            str(get_upload_to_hashed_path(None, 'foobar.mp4')).startswith('ad'),
        )
        self.assertFalse(
            str(get_upload_to_hashed_path(None, 'barbar-123.mov')).startswith('ad'),
        )
