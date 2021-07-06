from django.test import TestCase

from common.tests.factories.films import AssetFactory


class TestAsset(TestCase):
    maxDiff = None

    def test_clean_very_long_name_doesnt_break_because_slug_too_long(self):
        asset = AssetFactory(name='long name' * 10, slug='')
        asset.clean()
        asset.save()
        self.assertEqual(asset.slug, 'long-name' * 5 + 'long-')
