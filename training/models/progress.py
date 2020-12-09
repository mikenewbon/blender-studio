import datetime

from django.contrib.auth import get_user_model
from django.db import models

from common import mixins
from training.models import sections

User = get_user_model()


class UserSectionProgress(mixins.CreatedUpdatedMixin, models.Model):
    started_duration_pageview_duration = datetime.timedelta(seconds=5)
    finished_duration_pageview_duration = datetime.timedelta(minutes=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'section'], name='unique_progress_per_user_and_section'
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='section_progress')
    section = models.ForeignKey(sections.Section, on_delete=models.CASCADE, related_name='progress')

    started = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)

    def __str__(self) -> str:
        return (
            f'Progress of {self.user.username} ({self.user.id})'
            f' on Section {self.section.name} ({self.section.id})'
        )
