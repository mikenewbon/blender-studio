"""Add download counts from CloudFront logs imported into postgresql."""
# from pprint import pprint
import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from static_assets.models.static_assets import StaticAsset

logger = logging.getLogger('write_stats')
logger.setLevel(logging.WARNING)


class Command(BaseCommand):
    """Do subj."""

    def _read_source_downloads(self):
        source_hash_to_count = {}
        with open('cf_source_download_counts.csv', 'r') as f:
            for line in f.readlines():
                try:
                    source_hash = line.split(';')[0].strip().replace('"', '')
                    count = int(line.split(';')[1].strip().replace('"', ''))
                except ValueError:
                    logger.warning('Unable to parse %s', line)
                if source_hash not in source_hash_to_count:
                    source_hash_to_count[source_hash] = count
                else:
                    source_hash_to_count[source_hash] += count
        total = len(source_hash_to_count)

        seen_count = 0
        for source_hash in sorted(source_hash_to_count.keys()):
            try:
                count = source_hash_to_count[source_hash]
                try:
                    static_asset_q = StaticAsset.objects.filter(
                        Q(source__icontains=source_hash)
                        | Q(video__variations__source__icontains=source_hash)
                    )
                    static_asset = static_asset_q.get()
                    self._add_count(static_asset, count, source_hash)
                except StaticAsset.DoesNotExist:
                    pass
                except StaticAsset.MultipleObjectsReturned:
                    logger.error('Found multiple for %s: %s', source_hash, static_asset_q.all())
                    for static_asset in static_asset_q:
                        self._add_count(static_asset, count, source_hash)

                seen_count += 1
                if not seen_count % 500:
                    logger.warning('%s%% (%s/%s)', int(seen_count / total * 100), seen_count, total)
                    self._update()
            except Exception:
                logger.exception('Stopped at %s', source_hash)
                raise

        self._update()

    def _add_count(self, static_asset, count, source_hash):
        logger.info(
            '%s: %s download_count %s -> %s',
            source_hash,
            static_asset,
            static_asset.download_count,
            static_asset.download_count + count,
        )
        static_asset.download_count += count
        self.to_update.append(static_asset)

    def _update(self):
        StaticAsset.objects.bulk_update(
            self.to_update, fields={'date_updated', 'download_count'}, batch_size=500
        )
        self.to_update = []

    def handle(self, *args, **options):
        """Do subj."""
        self.to_update = []
        self._read_source_downloads()
