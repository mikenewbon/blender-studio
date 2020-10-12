from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import models
from django.urls.base import reverse

from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from films.models import Asset, Film, FilmCrew


class ProductionLog(mixins.CreatedUpdatedMixin, models.Model):
    """A log (collection) of all authors' production log entries in one week."""

    class Meta:
        verbose_name = 'production weekly'
        verbose_name_plural = 'production weeklies'

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='production_logs')
    name = models.CharField(
        'weekly title',
        max_length=512,
        blank=True,
        help_text='If not provided, will be set to <em>"This week on [film title]"</em>.',
    )
    name.description = 'If not provided, will be set to "This week on <film title>".'
    summary = models.TextField()
    start_date = models.DateField(default=date.today)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='uploaded_production_logs',
        verbose_name='created by',
    )
    user.description = 'The user who created the weekly production log.'
    author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='authored_production_logs',
        verbose_name='author (optional)',
        help_text='The actual author of the summary in the weekly production log',
    )
    author.description = 'The actual author of the summary in the weekly production log.'
    youtube_link = models.URLField(blank=True)
    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path)

    @property
    def author_name(self) -> str:
        """Get the production log summary's author full name.

        Usually the author of the log will be the same as the user who uploads it."""
        if self.author:
            return self.author.get_full_name()
        return self.user.get_full_name()

    @property
    def end_date(self):
        """The last day of a weekly log is the start_date + 6 days"""
        return self.start_date + timedelta(days=6)

    def clean(self):
        super().clean()
        if self.film_id:
            if not self.name:
                self.name = f'This week on {self.film.title}'

    def __str__(self):
        return f"{self.film.title} Production Weekly {self.start_date}"

    @property
    def admin_url(self) -> str:
        return reverse('admin:films_productionlog_change', args=[self.pk])


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

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='uploaded_log_entries',
        verbose_name='created by',
    )
    user.description = 'The user who created the production log entry.'
    author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='authored_log_entries',
        verbose_name='author (optional)',
        help_text='The actual author of the assets in the production log entry',
    )
    author.description = 'The actual author of the assets in the production log entry.'

    @property
    def author_role(self) -> str:
        """Find the role for the log entry author."""
        try:
            crew_member_role = FilmCrew.objects.values_list('role', flat=True).get(
                user=self.author, film=self.production_log.film
            )
        except FilmCrew.DoesNotExist:
            crew_member_role = ''

        return crew_member_role

    @property
    def author_name(self) -> str:
        """Get the production log entry's author full name.

        Usually the author of the log entry will be the same as the user who uploads the entry."""
        if self.author:
            return self.author.get_full_name() or self.author.username
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return (
            f'{self.production_log.film.title}: {self.author_name}\'s Production Weekly Entry '
            f'{self.production_log.start_date}'
        )

    @property
    def admin_url(self) -> str:
        return reverse('admin:films_productionlogentry_change', args=[self.pk])


class ProductionLogEntryAsset(models.Model):
    """This is an intermediary model between ProductionLogEntry and Asset.

    An ProductionLogEntryAsset should in fact only relate to one Asset, hence the
    OneToOne asset field.
    """

    class Meta:
        verbose_name = 'production weekly entry asset'

    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name='entry_asset')
    production_log_entry = models.ForeignKey(
        ProductionLogEntry, on_delete=models.CASCADE, related_name='entry_assets'
    )

    def __str__(self):
        return f'{self.asset.name} - {self.asset.date_created:%d %b %Y}'
