from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from static_assets.models import StorageLocation, DynamicStorageFileField

from common import mixins
from common.upload_paths import get_upload_to_hashed_path


class FilmStatus(models.TextChoices):
    in_development = '0_dev', 'In Development'
    in_production = '1_prod', 'In Production'
    released = '2_released', 'Released'


class Film(mixins.CreatedUpdatedMixin, models.Model):
    storage_location = models.OneToOneField(StorageLocation, on_delete=models.PROTECT)

    title = models.CharField(unique=True, max_length=512)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    description.description = 'Description consisting of a few sentences.'
    summary = models.TextField()
    summary.description = 'Summary consisting of multiple paragraphs.'

    status = models.TextField(choices=FilmStatus.choices)
    release_date = models.DateField(blank=True, null=True)
    release_date.description = "Past or planned release date of the film."
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    logo = DynamicStorageFileField(upload_to=get_upload_to_hashed_path)
    poster = DynamicStorageFileField(upload_to=get_upload_to_hashed_path)
    picture_header = DynamicStorageFileField(upload_to=get_upload_to_hashed_path)
    picture_16_9 = DynamicStorageFileField(
        upload_to=get_upload_to_hashed_path, blank=True, null=True
    )
    youtube_link = models.URLField(blank=True)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.title)

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse('film-detail', kwargs={'film_slug': self.slug})

    @property
    def admin_url(self) -> str:
        return reverse('admin:films_film_change', args=[self.pk])
