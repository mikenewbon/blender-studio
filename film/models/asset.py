from pathlib import Path

from django.db import models

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


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='assets')
    file = models.FileField(upload_to=asset_upload_path)
    size = models.IntegerField()

    def __str__(self) -> str:
        return self.file.path  # type: ignore
