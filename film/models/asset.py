from pathlib import Path

from django.db import models
from django.utils.text import slugify

from common import mixins
from film.models.collection import Collection


def asset_upload_path(asset: 'Asset', filename: str) -> str:
    return str(
        Path('film')
        / str(asset.collection.film_id)
        / 'collection'
        / str(asset.collection_id)
        / 'assets'
        / filename
    )


class Video(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='videos')
    file = models.FileField(upload_to=asset_upload_path)
    size = models.IntegerField()
    duration = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')

    def __str__(self) -> str:
        return self.file.path  # type: ignore


class Image(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='videos')
    file = models.ImageField(upload_to=asset_upload_path)  # height_field? width_field?
    size = models.IntegerField()

    def __str__(self) -> str:
        return self.file.path  # type: ignore


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='assets')
    index = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    text = models.TextField()  # or description?

    # author?

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return self.file.path  # type: ignore
