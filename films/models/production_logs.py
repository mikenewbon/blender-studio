from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import models

from common import mixins
from films.models import Asset, Film


class LogGroup(mixins.CreatedUpdatedMixin, models.Model):
    """ A log (collection) of all authors' production logs in one week. """

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='log_groups')
    description = models.TextField()
    week_number = models.PositiveSmallIntegerField()
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        self.end_date = self.start_date + timedelta(days=7)


class ProductionLog(mixins.CreatedUpdatedMixin, models.Model):
    """ A log (collection) of assets created by one author during one week. """

    log_group = models.ForeignKey(
        LogGroup, on_delete=models.CASCADE, related_name='production_logs'
    )
    description = models.TextField()

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_logs')
    user.description = "The user who uploaded the production log."
    author = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.PROTECT, related_name='authored_logs'
    )
    author.description = "The actual author of the assets in the production log."
    author_role = models.CharField(max_length=512)

    @property
    def author_name(self) -> str:
        """ Get the production log's author full name.

        Usually the author of the log will be the same as the user who uploads the log. """
        if self.author:
            return self.author.get_full_name()
        return self.user.get_full_name()

    # def clean(self):
    #     super().clean()
    #     if not self.log_group:
    #         ...  # get_or_create? + add blank=True in log_group field


class ProductionLogAsset(models.Model):
    """ This is an intermediary model between ProductionLog and Asset.

    An ProductionLogAsset should in fact only relate to one Asset, hence the
    OneToOne asset field.
    """

    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    production_log = models.ForeignKey(ProductionLog, on_delete=models.CASCADE)
