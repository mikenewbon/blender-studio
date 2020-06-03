from pathlib import Path

from django.db import models
from django.utils.text import slugify

from common import mixins
from films.models import films


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
                fields=['parent', 'order'], name='unique_ordering_per_collection'
            ),
            models.UniqueConstraint(fields=['parent', 'slug'], name='unique_slug_per_collection'),
        ]

    film = models.ForeignKey(films.Film, on_delete=models.CASCADE, related_name='collections')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_collections'
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
        return self.name
