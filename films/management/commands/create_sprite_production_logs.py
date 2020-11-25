# noqa: D100
from datetime import timedelta, datetime

import films.models as models_films
from cloud_import.management.mixins import ImportCommand


MONDAY, SUNDAY = 0, 6
weekdays = 6


class Command(ImportCommand):
    """Create production logs for Sprite."""

    help = 'Create production logs for Sprite Fright'

    def handle(self, *args, **options):  # noqa: D102
        film = models_films.Film.objects.get(slug='sprite-fright')
        earliest_asset = film.assets.order_by('date_created')[0]
        latest_asset = film.assets.order_by('-date_created')[0]
        date_start = earliest_asset.date_created.date()
        if date_start.weekday() != MONDAY:
            date_start = date_start - timedelta(days=date_start.weekday())
        date_end = latest_asset.date_created.date()
        if date_end.weekday() != SUNDAY:
            date_end = date_end + timedelta(days=(SUNDAY - date_end.weekday()))
        self.console_log(f'Production logs start at {date_start}, end at {date_end}')

        production_log_index = 1
        monday = date_start

        while monday < date_end:
            assert monday.weekday() == MONDAY, f'{monday} is not a monday: {monday.weekday()}'
            sunday = monday + timedelta(days=weekdays)
            assert sunday.weekday() == SUNDAY, f'{sunday} is not a sunday: {sunday.weekday()}'
            self.console_log(f'Assets from {monday} to {sunday}')
            next_monday = monday + timedelta(days=weekdays + 1)
            assert (
                next_monday.weekday() == MONDAY
            ), f'{next_monday} is not a monday: {next_monday.weekday()}'
            assets = film.assets.filter(
                date_created__gte=datetime.combine(monday, datetime.min.time()),
                date_created__lt=datetime.combine(next_monday, datetime.min.time()),
            ).order_by('date_created')
            if not assets.count():
                self.console_log(f'No entries on {monday} to {sunday}')
                monday = next_monday
                continue

            some_asset = assets[0]
            production_log_date = some_asset.date_created
            production_log_author = some_asset.static_asset.author or some_asset.static_asset.user

            production_log_name = (
                f'#{production_log_index} - {production_log_date.strftime("%d %B, %Y")}'
            )
            production_log = models_films.ProductionLog.objects.create(
                film=film,
                name=production_log_name,
                start_date=production_log_date,
                user=production_log_author,
            )
            production_log.date_created = monday
            production_log.date_updated = monday
            production_log.save(update_fields=['date_created', 'date_updated'])

            assets_per_user = {}
            users_per_pk = {}
            for asset in assets:
                asset_author = asset.static_asset.author or asset.static_asset.user
                assert asset_author, f'Missing asset author for {asset}'
                if asset_author.pk not in assets_per_user:
                    assets_per_user[asset_author.pk] = []
                if asset_author.pk not in users_per_pk:
                    users_per_pk[asset_author.pk] = asset_author
                assets_per_user[asset_author.pk].append(asset)

            for user_id, authored_assets in assets_per_user.items():
                user = users_per_pk[user_id]
                if not len(authored_assets):
                    self.console_log(f'Empty asset set for {user}, skipping')
                    continue
                production_log_entry = models_films.ProductionLogEntry.objects.create(
                    production_log=production_log,
                    user=user,
                )
                production_log_entry.date_created = authored_assets[0].date_created
                production_log_entry.date_updated = authored_assets[0].date_created
                production_log_entry.save(update_fields=['date_created', 'date_updated'])

                for authored_asset in authored_assets:
                    self.console_log(f'Adding {authored_asset} to {production_log_entry}')
                    models_films.ProductionLogEntryAsset.objects.get_or_create(
                        asset=authored_asset,
                        production_log_entry=production_log_entry,
                    )

            production_log_index += 1
            monday = next_monday
