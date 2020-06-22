from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import models

from assets.models import DynamicStorageFileField, StorageBackend
from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from films.models import Asset, Film


class ProductionLog(mixins.CreatedUpdatedMixin, models.Model):
    """A log (collection) of all authors' production log entries in one week."""

    class Meta:
        verbose_name = 'production weekly'
        verbose_name_plural = 'production weeklies'

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='production_logs')
    name = models.CharField(max_length=512, blank=True)
    name.description = 'If not provided, will be set to "This week on <film title>".'
    description = models.TextField()
    start_date = models.DateField(default=date.today)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='production_logs')
    youtube_link = models.URLField(blank=True)
    storage_backend = models.ForeignKey(
        StorageBackend, on_delete=models.CASCADE, related_name='production_logs'
    )
    picture_16_9 = DynamicStorageFileField(upload_to=get_upload_to_hashed_path)

    @property
    def end_date(self):
        return self.start_date + timedelta(days=7)

    def clean(self):
        super().clean()
        if not self.name:
            self.name = f'This week on {self.film.title}'

    def __str__(self):
        return f"{self.film.title} Production Weekly {self.start_date}"


class ProductionLogEntry(mixins.CreatedUpdatedMixin, models.Model):
    """A collection of assets created by one author during one week."""

    class Meta:
        verbose_name = 'production weekly entry'
        verbose_name_plural = 'production weekly entries'

    production_log = models.ForeignKey(
        ProductionLog,
        on_delete=models.CASCADE,
        related_name='log_entries',
        verbose_name='production weekly',
    )
    description = models.TextField()

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_log_entries')
    user.description = "The user who uploaded the production log entry."
    author = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.PROTECT, related_name='authored_log_entries'
    )
    author.description = "The actual author of the assets in the production log entry."
    author_role = models.CharField(max_length=512)

    @property
    def author_name(self) -> str:
        """Get the production log entry's author full name.

        Usually the author of the log entry will be the same as the user who uploads the entry."""
        if self.author:
            return self.author.get_full_name()
        return self.user.get_full_name()

    def __str__(self):
        return (
            f'{self.production_log.film.title}: {self.author_name}\'s Production Weekly Entry '
            f'{self.production_log.start_date}'
        )


class ProductionLogEntryAsset(models.Model):
    """This is an intermediary model between ProductionLogEntry and Asset.

    An ProductionLogEntryAsset should in fact only relate to one Asset, hence the
    OneToOne asset field.
    """

    class Meta:
        verbose_name = 'production weekly entry asset'

    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    production_log_entry = models.ForeignKey(
        ProductionLogEntry, on_delete=models.CASCADE, related_name='entry_assets'
    )

    def __str__(self):
        return f'{self.asset.name} - {self.asset.date_created:%d %b %Y}'
