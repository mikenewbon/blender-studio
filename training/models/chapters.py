from django.db import models
from django.urls.base import reverse
from django.utils.text import slugify

from common import mixins
from training.models import trainings


class Chapter(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['training', 'index'], name='unique_index_per_chapter'),
            models.UniqueConstraint(fields=['training', 'slug'], name='unique_slug_per_chapter'),
        ]

    training = models.ForeignKey(
        trainings.Training, on_delete=models.CASCADE, related_name='chapters'
    )
    index = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)

    def clean(self) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return f'{self.training.name} > {self.index:02.0f}. {self.name}'

    @property
    def admin_url(self) -> str:
        return reverse('admin:training_chapter_change', args=[self.pk])
