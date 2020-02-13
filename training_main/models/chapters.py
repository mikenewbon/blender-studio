from django.db import models

from training_main.models import mixins, trainings


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
    slug = models.TextField(unique=True)

    def __str__(self) -> str:
        return f'{self.index} {self.name}'
