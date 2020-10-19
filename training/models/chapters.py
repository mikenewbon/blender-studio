import uuid
from django.db import models
from django.urls.base import reverse
from django.contrib.auth.models import User

from common.upload_paths import get_upload_to_hashed_path
from common import mixins
from training.models import trainings


class Chapter(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        ordering = ['index', 'name']

    training = models.ForeignKey(
        trainings.Training, on_delete=models.CASCADE, related_name='chapters'
    )
    index = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(unique=True, null=False)
    description = models.TextField(blank=True)
    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = uuid.uuid4().hex

    def __str__(self) -> str:
        return f'{self.training.name} > {self.index:02.0f}. {self.name}'

    @property
    def admin_url(self) -> str:
        return reverse('admin:training_chapter_change', args=[self.pk])
