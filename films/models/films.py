from pathlib import Path

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from assets.models import StorageBackend
from common import mixins


class FilmStatus(models.TextChoices):
    in_development = 'pre_production', 'In Development'
    in_production = 'in_production', 'In Production'
    released = 'released', 'Released'


def film_overview_upload_path(film: 'Film', filename: str) -> str:
    return str(Path('films') / str(film.id) / 'overview' / filename)


class Film(mixins.CreatedUpdatedMixin, models.Model):
    storage = models.OneToOneField(StorageBackend, on_delete=models.PROTECT)
    # TODO: validation - either film or a training has to be null, but not both

    title = models.TextField(unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    description.description = 'Description consisting of a few sentences.'
    summary = models.TextField()
    summary.description = 'Summary consisting of multiple paragraphs.'

    status = models.TextField(choices=FilmStatus.choices)
    visibility = models.BooleanField(default=False)

    logo = models.FileField(upload_to=film_overview_upload_path)
    poster = models.FileField(upload_to=film_overview_upload_path)
    picture_header = models.FileField(upload_to=film_overview_upload_path, blank=True, null=True)
    picture_16_9 = models.FileField(upload_to=film_overview_upload_path, blank=True, null=True)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.title)

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return self.url

    # @property
    # def url(self) -> str:
    #     return reverse('film', kwargs={'film_slug': self.slug})


# TODO: tags, comments
