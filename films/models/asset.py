from pathlib import Path

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify

from common import mixins
from films.models.collection import Collection
from films.models.film import Film
from films.models.license import License


class AssetCategory(models.TextChoices):
    artwork = 'artwork', 'Artwork'
    production_file = 'production_file', 'Production File'
    production_lesson = 'production_lesson', 'Production Lesson'


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    """ This represents the leaf of the tree of film-related resources. """

    class Meta:
        constraints = []  # TODO: only one related file (img, video, file)

    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    collection = models.ForeignKey(
        Collection, blank=True, null=True, on_delete=models.CASCADE, related_name='assets'
    )
    order = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    text = models.TextField()
    license = models.ForeignKey(License, on_delete=models.PROTECT)

    category = models.CharField(choices=AssetCategory.choices, max_length=17)

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    user.description = "The user who uploaded the asset."
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    author.description = "The actual author of the asset."
    view_count = models.PositiveIntegerField()

    visibility = models.BooleanField(default=False)

    @property
    def picture_16_9(self):
        # TODO: get appropriate picture from the related img/video/file
        pass

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return self.name


def asset_upload_path(asset: 'Asset', filename: str) -> str:
    return str(
        Path('film')
        / str(asset.collection.film_id)
        / 'collection'
        / str(asset.collection_id)
        / 'assets'
        / filename
    )


class Video(Asset):
    file = models.FileField(upload_to=asset_upload_path)
    size_bytes = models.IntegerField()
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)
    duration_seconds = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    preview = models.ImageField(upload_to=asset_upload_path)

    play_count = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.file.path} in {self.name}"


class Image(Asset):
    file = models.ImageField(upload_to=asset_upload_path)
    size_bytes = models.IntegerField()
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.file.path} in {self.name}"


class File(Asset):
    file = models.FileField(upload_to=asset_upload_path)
    size_bytes = models.IntegerField()
    preview = models.ImageField(upload_to=asset_upload_path)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.file.path} in {self.name}"
