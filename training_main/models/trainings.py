from django.contrib.auth.models import User
from django.db import models

from training_main.models import mixins, tags


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

    name = models.TextField(unique=True)
    slug = models.TextField(unique=True)
    description = models.TextField()
    description.description = 'Description consisting of a few sentences.'
    summary = models.TextField()
    summary.description = 'Summary consisting of multiple paragraphs.'

    status = models.TextField(choices=TrainingStatus.choices)

    tags = models.ManyToManyField(tags.Tag, through='TrainingTag', related_name='trainings')
    type = models.TextField(choices=TrainingType.choices)
    difficulty = models.TextField(choices=TrainingDifficulty.choices)

    favorited_by = models.ManyToManyField(
        User, through='TrainingFavorite', related_name='favorite_trainings'
    )

    def __str__(self) -> str:
        return self.name


class TrainingTag(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['training', 'tag'], name='unique_tags_per_training')
        ]

    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    tag = models.ForeignKey(tags.Tag, on_delete=models.CASCADE)


class TrainingFavorite(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'training'], name='unique_favourite_per_user_and_training'
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    training = models.ForeignKey(Training, on_delete=models.CASCADE)
