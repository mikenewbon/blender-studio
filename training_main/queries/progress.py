import datetime

from training_main.models import progress


def set_video_progress(*, user_pk: int, video_pk: int, position: datetime.timedelta) -> None:
    progress.UserVideoProgress.objects.update_or_create(
        user_id=user_pk, video_id=video_pk, defaults={'position': position}
    )
