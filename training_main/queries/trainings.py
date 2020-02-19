from typing import Optional, List, Tuple, cast

from django.db.models import QuerySet, Exists, OuterRef, Max

from training_main.models import trainings, chapters


def _published() -> 'QuerySet[trainings.Training]':
    return trainings.Training.objects.filter(status=trainings.TrainingStatus.published)


def set_favorite(*, training_pk: int, user_pk: int, favorite: bool) -> None:
    if favorite:
        trainings.Favorite.objects.filter(
            training__status=trainings.TrainingStatus.published
        ).update_or_create(
            training_id=training_pk, user_id=user_pk,
        )
    else:
        trainings.Favorite.objects.filter(
            training__status=trainings.TrainingStatus.published,
            training_id=training_pk,
            user_id=user_pk,
        ).delete()


def from_slug_with_chapters(
    *, user_pk: int, training_slug: str,
) -> Optional[Tuple[trainings.Training, bool, List[chapters.Chapter]]]:
    try:
        training = (
            _published()
            .annotate(
                favorited=Exists(
                    trainings.Favorite.objects.filter(user_id=user_pk, training_id=OuterRef('pk'))
                )
            )
            .prefetch_related('tags', 'chapters')
            .get(slug=training_slug)
        )
    except trainings.Training.DoesNotExist:
        return None

    return training, cast(bool, getattr(training, 'favorited')), list(training.chapters.all())


def recently_watched(*, user_pk: int) -> List[trainings.Training]:
    return list(
        _published()
        .annotate(date_last_watched=Max('chapters__sections__progress__date_updated'))
        .prefetch_related('tags')
        .exclude(date_last_watched__isnull=True)
        .order_by('-date_last_watched')
    )


def favorited(*, user_pk: int) -> List[trainings.Training]:
    return list(
        _published()
        .prefetch_related('tags')
        .filter(favorites__user_id=user_pk)
        .order_by('-favorites__date_created')
    )


def all(user_pk: Optional[int]) -> List[trainings.Training]:
    return list(
        _published()
        .exclude(
            chapters__sections__progress__user_id=user_pk,
            chapters__sections__progress__started=True,
            chapters__sections__progress__finished=False,
        )
        .exclude(favorites__user_id=user_pk)
        .prefetch_related('tags')
        .order_by('-date_created')
    )
