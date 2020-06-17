from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import models

from common import mixins
from films.models import Asset, Film


class ProductionLog(mixins.CreatedUpdatedMixin, models.Model):
    """A log (collection) of all authors' production log entries in one week."""

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='production_logs')
    description = models.TextField()
    start_date = models.DateField(default=date.today)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    @property
    def end_date(self):
        return self.start_date + timedelta(days=7)


class ProductionLogEntry(mixins.CreatedUpdatedMixin, models.Model):
    """A collection of assets created by one author during one week."""

    log_group = models.ForeignKey(
        ProductionLog, on_delete=models.CASCADE, related_name='log_entries'
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


class ProductionLogEntryAsset(models.Model):
    """This is an intermediary model between ProductionLogEntry and Asset.

    An ProductionLogEntryAsset should in fact only relate to one Asset, hence the
    OneToOne asset field.
    """

    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    production_log_entry = models.ForeignKey(ProductionLogEntry, on_delete=models.CASCADE)
