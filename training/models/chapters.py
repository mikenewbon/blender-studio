from django.db import models

from common import mixins
from training.models import trainings


class Chapter(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['training', 'index'], name='unique_index_per_chapter'),
        ]

    training = models.ForeignKey(
        trainings.Training, on_delete=models.CASCADE, related_name='chapters'
    )
    index = models.IntegerField()

    name = models.TextField(unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:
        return f'{self.training.name} > {self.index:02.0f}. {self.name}'
