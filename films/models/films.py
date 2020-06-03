from django.db import models
from django.utils.text import slugify

from assets.models import StorageBackend
from common import mixins
from common.upload_paths import get_upload_to_hashed_path


class FilmStatus(models.TextChoices):
    in_development = 'pre_production', 'In Development'
    in_production = 'in_production', 'In Production'
    released = 'released', 'Released'


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

    logo = models.ImageField(upload_to=get_upload_to_hashed_path)
    poster = models.ImageField(upload_to=get_upload_to_hashed_path)
    picture_header = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True, null=True)
    picture_16_9 = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True, null=True)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.title)

    def __str__(self) -> str:
        return self.title

    # def get_absolute_url(self) -> str:
    #     return self.url

    # @property
    # def url(self) -> str:
    #     return reverse('film', kwargs={'film_slug': self.slug})


# TODO: tags
