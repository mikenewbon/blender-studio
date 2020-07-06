from django.contrib.auth.models import User
from django.db import models
from django.urls.base import reverse
from django.utils.text import slugify

from assets.models import StorageLocation, DynamicStorageFileField
from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from training.models import tags


class TrainingStatus(models.TextChoices):
    published = 'published', 'Published'
    unpublished = 'unpublished', 'Unpublished'


class TrainingType(models.TextChoices):
    workshop = 'workshop', 'Workshop'
    course = 'course', 'Course'
    production_lesson = 'production_lesson', 'Production Lesson'


class TrainingDifficulty(models.TextChoices):
    beginner = 'beginner', 'Beginner'
    intermediate = 'intermediate', 'Intermediate'
    advanced = 'advanced', 'Advanced'


class Training(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['status', 'type', 'difficulty']),
            models.Index(fields=['status', 'difficulty', 'type']),
        ]

    storage_location = models.OneToOneField(StorageLocation, on_delete=models.PROTECT)
    # TODO(Natalia): validation - either film or a training has to be null, but not both

    name = models.CharField(unique=True, max_length=512)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    description.description = 'Description consisting of a few sentences.'
    summary = models.TextField()
    summary.description = 'Summary consisting of multiple paragraphs.'

    status = models.TextField(choices=TrainingStatus.choices)
    is_featured = models.BooleanField(default=False)

    tags = models.ManyToManyField(tags.Tag, through='TrainingTag', related_name='trainings')
    type = models.TextField(choices=TrainingType.choices)
    difficulty = models.TextField(choices=TrainingDifficulty.choices)
    picture_header = DynamicStorageFileField(
        upload_to=get_upload_to_hashed_path, blank=True, null=True
    )
    picture_16_9 = DynamicStorageFileField(
        upload_to=get_upload_to_hashed_path, blank=True, null=True
    )

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
        return reverse('training_favorite', kwargs={'training_pk': self.pk})

    @property
    def admin_url(self) -> str:
        return reverse('admin:training_training_change', args=[self.pk])


class TrainingTag(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['training', 'tag'], name='unique_tags_per_training')
        ]

    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    tag = models.ForeignKey(tags.Tag, on_delete=models.CASCADE)


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
