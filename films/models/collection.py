from pathlib import Path

from django.db import models
from django.utils.text import slugify

from common import mixins
from films.models import film


def collection_overview_upload_path(collection: 'Collection', filename: str) -> str:
    return str(
        Path('films')
        / str(collection.film.id)
        / 'collections'
        / str(collection.id)
        / 'overview'
        / filename
    )


class Collection(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['parent_collection', 'index'], name='unique_index_per_collection'
            ),
            models.UniqueConstraint(
                fields=['parent_collection', 'slug'], name='unique_slug_per_collection'
            ),
        ]

    film = models.ForeignKey(film.Film, on_delete=models.CASCADE, related_name='collections')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, related_name='child_collections'
    )
    order = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    text = models.TextField()

    picture_16_9 = models.FileField(
        upload_to=collection_overview_upload_path, blank=True, null=True
    )

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self):
        return self.name  # for the time being
