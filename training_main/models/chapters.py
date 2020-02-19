from django.db import models
from django.urls.base import reverse

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
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:
        return f'{self.training.name} > {self.index:02.0f}. {self.name}'

    @property
    def url(self) -> str:
        return reverse(
            'chapter',
            kwargs={
                'training_slug': self.training.slug,
                'chapter_index': self.index,
                'chapter_slug': self.slug,
            },
        )
