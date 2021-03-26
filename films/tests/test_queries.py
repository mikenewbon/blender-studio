import random

from django.test import TestCase

from common.tests.factories.films import AssetFactory
from films.models.assets import Asset
from films.queries import get_random_featured_assets


class TestQueries(TestCase):
    def test_get_random_featured_assets_from_a_larger_number_of_assets(self):
        total_assets = 20
        for i in range(total_assets):
            AssetFactory(is_featured=bool(i % 3))

        random_assets = get_random_featured_assets(limit=3)

        self.assertEqual(len(random_assets), 3)
        # Must be unique assets
        self.assertEqual(len(random_assets), len({asset.pk for asset in random_assets}))

    def test_get_random_featured_assets_from_a_smaller_number_of_assets(self):
        total_assets = 15
        for i in range(total_assets):
            AssetFactory(is_featured=i >= 5)
        self.assertTrue(Asset.objects.filter(is_published=True, is_featured=True).count() == 10)

        random_assets = get_random_featured_assets(limit=11)

        self.assertEqual(len(random_assets), 10)
        asset_ids = [asset.pk for asset in random_assets]
        # Must be unique assets
        self.assertEqual(len(random_assets), len(set(asset_ids)))

    def test_get_random_featured_assets_empty_assets(self):
        self.assertEqual(Asset.objects.count(), 0)

        random_assets = get_random_featured_assets(limit=3)

        self.assertEqual(random_assets, [])

    def test_get_random_featured_assets_no_featured_assets(self):
        total_assets = 20
        for _ in range(total_assets):
            AssetFactory(is_featured=False)

        random_assets = get_random_featured_assets(limit=3)

        self.assertEqual(random_assets, [])

    def test_get_random_featured_assets_returns_different_records(self):
        total_assets = 20
        for _ in range(total_assets):
            AssetFactory(is_featured=random.randint(1, 2) == 2)

        random_assets1 = get_random_featured_assets(limit=3)
        random_assets2 = get_random_featured_assets(limit=3)

        self.assertEqual(len(random_assets1), 3)
        self.assertEqual(len(random_assets2), 3)

        # Must be unique assets
        self.assertEqual(len(random_assets1), len({asset.pk for asset in random_assets1}))
        self.assertEqual(len(random_assets2), len({asset.pk for asset in random_assets2}))
        # That's no necessarily true all the time, but most of the times this test should not fail
        self.assertNotEqual({a.pk for a in random_assets1}, {a.pk for a in random_assets2})
