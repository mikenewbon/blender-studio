from django.contrib.auth.models import User
from django.db import models

from training_main.models import mixins, sections


class UserVideoProgress(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'video'], name='unique_progress_per_user_and_video'
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(sections.Video, on_delete=models.CASCADE, related_name='progress')

    position = models.DurationField()


class UserSectionProgress(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'section'], name='unique_progress_per_user_and_section'
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='section_progress')
    section = models.ForeignKey(sections.Section, on_delete=models.CASCADE, related_name='progress')

    # TODO(sem): Figure out when to set `started = True`.
    started = models.BooleanField()
    # TODO(sem): Figure out when to set `finished = True`.
    finished = models.BooleanField()
