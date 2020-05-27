from django.db import models

from common import mixins
from film.models import film


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
    parent_collection = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, related_name='child_collections'
    )
    index = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    text = models.TextField()  # or description?

    def __str__(self):
        return self.name  # for the time being
