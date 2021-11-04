"""Aggregate views/downloads from CloudFront logs imported into postgresql."""
# from pprint import pprint
import logging

from django.core.management.base import BaseCommand

from static_assets.models.static_assets import StaticAsset
from training.models.sections import Section
from films.models.assets import Asset

logger = logging.getLogger('write_stats')
logger.setLevel(logging.DEBUG)


class Command(BaseCommand):
    """Do subj."""

    def _read_film_asset_view_counts(self):
        asset_id_to_count = {}
        with open('cf_film_asset_view_counts.csv', 'r') as f:
            for line in f.readlines():
                try:
                    asset_id = int(
                        line.split(';')[0]
                        .strip()
                        .replace('"', '')
                        .replace(')', '')
                        .replace('(', '')
                    )
                    count = int(line.split(';')[1].strip().replace('"', ''))
                except ValueError:
                    logger.warning('Unable to parse %s', line)
                if asset_id not in asset_id_to_count:
                    asset_id_to_count[asset_id] = count
                else:
                    asset_id_to_count[asset_id] += count

        to_update = []
        for asset_id, count in asset_id_to_count.items():
            asset_q = Asset.objects.filter(pk=asset_id)
            if not asset_q.exists():
                continue
            asset = asset_q.get()
            static_asset = asset.static_asset
            logger.info(
                '%s: %s view_count %s -> %s',
                asset_id,
                static_asset,
                static_asset.view_count,
                static_asset.view_count + count,
            )
            static_asset.view_count += count
            to_update.append(static_asset)

        self._update(to_update)

    def _read_training_section_view_counts(self):
        section_slug_to_count = {}
        with open('cf_training_section_view_counts.csv', 'r') as f:
            for line in f.readlines():
                try:
                    training_uri = line.split(';')[0].strip().replace('"', '')
                    _, training_slug, section_slug = training_uri.split('/')[:3]
                    count = int(line.split(';')[1].strip().replace('"', ''))
                except ValueError:
                    logger.warning('Unable to parse %s', line)
                if section_slug not in section_slug_to_count:
                    section_slug_to_count[section_slug] = count
                else:
                    section_slug_to_count[section_slug] += count

        to_update = []
        for section_slug, count in section_slug_to_count.items():
            section_q = Section.objects.filter(slug=section_slug)
            if not section_q.exists():
                continue
            section = section_q.get()
            static_asset = section.static_asset
            if not static_asset:
                logger.warning('%s: no static asset', section_slug)
                continue
            logger.info(
                '%s: %s view_count %s -> %s',
                section_slug,
                static_asset,
                static_asset.view_count,
                static_asset.view_count + count,
            )
            static_asset.view_count += count
            to_update.append(static_asset)

        self._update(to_update)

    def _update(self, to_update):
        StaticAsset.objects.bulk_update(
            to_update, fields={'date_updated', 'view_count'}, batch_size=500
        )

    def handle(self, *args, **options):
        """Do subj."""
        self._read_film_asset_view_counts()

        self._read_training_section_view_counts()
