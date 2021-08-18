from django.test import TestCase

from common.tests.factories.films import ProductionLogEntryAssetFactory
from common.tests.factories.users import UserFactory


class TestProductionLogs(TestCase):
    def test_production_entry_contributors(self):
        entry_asset1 = ProductionLogEntryAssetFactory()
        entry_asset1.asset.static_asset.contributors.add(UserFactory(), UserFactory())
        self.assertEqual(entry_asset1.asset.static_asset.contributors.count(), 2)

        entry_asset2 = ProductionLogEntryAssetFactory(
            production_log_entry=entry_asset1.production_log_entry
        )
        entry_asset2.asset.static_asset.contributors.add(UserFactory())
        self.assertEqual(entry_asset2.asset.static_asset.contributors.count(), 1)

        # Check that the entry has 3 contributors in total
        self.assertEqual(len(entry_asset1.production_log_entry.contributors), 3)
