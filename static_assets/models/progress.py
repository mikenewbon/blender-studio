from django.db import models
from django.contrib.auth import get_user_model

from common import mixins
import static_assets.models as models_static_assets

User = get_user_model()


class UserVideoProgress(mixins.CreatedUpdatedMixin, models.Model):
    section_completion_fraction = 0.8

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'video'], name='unique_progress_per_user_and_video'
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_progress')
    video = models.ForeignKey(
        models_static_assets.Video, on_delete=models.CASCADE, related_name='progress'
    )

    position = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')

    def __str__(self) -> str:
        return f'Progress of {self.user.username} ({self.user.id}) on Video {self.video.id}'
