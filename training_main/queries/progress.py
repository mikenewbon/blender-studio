import datetime

from training_main.models import progress


def set_video_progress(*, user_pk: int, video_pk: int, position: datetime.timedelta) -> None:
    progress.UserVideoProgress.objects.update_or_create(
        user_id=user_pk, video_id=video_pk, defaults={'position': position}
    )


def set_section_progress_started(*, user_pk: int, section_pk: int) -> None:
    progress.UserSectionProgress.objects.update_or_create(
        user_id=user_pk, section_id=section_pk, defaults={'started': True}
    )


def set_section_progress_finished(*, user_pk: int, section_pk: int) -> None:
    progress.UserSectionProgress.objects.update_or_create(
        user_id=user_pk, section_id=section_pk, defaults={'started': True, 'finished': True}
    )
