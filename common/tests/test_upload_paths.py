from django.test.testcases import TestCase
from pathlib import PosixPath
from unittest.mock import patch

from common.upload_paths import generate_hash_from_filename, get_upload_to_hashed_path


@patch('common.upload_paths.uuid.uuid4', return_value='e8b542ae-97fc-4a3b-bae7-578f330945ba')
class TestUploadPaths(TestCase):
    def test_generate_hash_from_filename(self, _):
        self.assertEqual(
            generate_hash_from_filename('awesome-123.mov'), '60aaaae7629fdb4d40621e677c029cc0'
        )

    def test_get_upload_to_hashed_path(self, _):
        self.assertEqual(
            get_upload_to_hashed_path(None, 'awesome-123.mov'),
            PosixPath('60/60aaaae7629fdb4d40621e677c029cc0/60aaaae7629fdb4d40621e677c029cc0.mov'),
        )
