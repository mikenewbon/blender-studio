import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.urls.base import reverse

from common.upload_paths import get_upload_to_hashed_path
from common import mixins
from training.models import trainings

User = get_user_model()


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
    picture_header = models.FileField(upload_to=get_upload_to_hashed_path, null=True, blank=True)
    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    is_published = models.BooleanField(default=False)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = uuid.uuid4().hex

    def __str__(self) -> str:
        return f'{self.training.name} > {self.index:02.0f}. {self.name}'

    @property
    def url(self) -> str:
        return reverse(
            'chapter',
            kwargs={'training_slug': self.training.slug, 'chapter_slug': self.slug},
        )

    @property
    def admin_url(self) -> str:
        return reverse('admin:training_chapter_change', args=[self.pk])
