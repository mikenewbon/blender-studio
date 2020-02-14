from typing import Optional, List, Tuple

from django.contrib.auth.models import User
from django.db.models import QuerySet

from training_main.models import trainings, chapters


def _published() -> 'QuerySet[trainings.Training]':
    return trainings.Training.objects.filter(status=trainings.TrainingStatus.published)


def from_slug_with_chapters(
    slug: str,
) -> Optional[Tuple[trainings.Training, List[chapters.Chapter]]]:
    try:
        training = _published().prefetch_related('chapters').get(slug=slug)
        return training, list(training.chapters.all())
    except trainings.Training.DoesNotExist:
        return None


def favorited(*, user: User) -> List[trainings.Training]:
    return list(_published().filter(favorites__user=user).order_by('-favorites__date_created'))


def recently_watched(*, user: User) -> List[trainings.Training]:
    return list(
        _published().filter(
            chapters__sections__progress__user=user,
            chapters__sections__progress__started=True,
            chapters__sections__progress__finished=False,
        )
    )


def all() -> List[trainings.Training]:
    return list(_published().order_by('-date_created'))
