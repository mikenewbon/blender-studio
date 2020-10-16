from django.contrib.auth.models import User
from django.db import models
from django.urls.base import reverse
from django.utils.text import slugify
from taggit.managers import TaggableManager

from common import mixins
from common.upload_paths import get_upload_to_hashed_path


class TrainingStatus(models.TextChoices):
    published = 'published', 'Published'
    unpublished = 'unpublished', 'Unpublished'


class TrainingType(models.TextChoices):
    workshop = 'workshop', 'Workshop'
    course = 'course', 'Course'


class TrainingDifficulty(models.TextChoices):
    beginner = 'beginner', 'Beginner'
    intermediate = 'intermediate', 'Intermediate'
    advanced = 'advanced', 'Advanced'


class Training(mixins.CreatedUpdatedMixin, mixins.StaticThumbnailURLMixin, models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['status', 'type', 'difficulty']),
            models.Index(fields=['status', 'difficulty', 'type']),
        ]

    name = models.CharField(unique=True, max_length=512)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    description.description = 'Description consisting of a few sentences.'
    summary = models.TextField()
    summary.description = 'Summary consisting of multiple paragraphs.'

    status = models.TextField(choices=TrainingStatus.choices)
    is_featured = models.BooleanField(default=False)

    tags = TaggableManager(blank=True)

    type = models.TextField(choices=TrainingType.choices)
    difficulty = models.TextField(choices=TrainingDifficulty.choices)
    picture_header = models.FileField(upload_to=get_upload_to_hashed_path)
    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path)

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return self.url

    @property
    def url(self) -> str:
        return reverse('training', kwargs={'training_slug': self.slug})

    @property
    def favorite_url(self) -> str:
        return reverse('training-favorite', kwargs={'training_pk': self.pk})

    @property
    def admin_url(self) -> str:
        return reverse('admin:training_training_change', args=[self.pk])


class Favorite(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'training'], name='unique_favourite_per_user_and_training'
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='favorites')

    def __str__(self) -> str:
        return (
            f'Favorite of {self.user.username} ({self.user.id}) on Training '
            f'{self.training.name} ({self.training.id})'
        )
