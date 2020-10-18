from typing import List, Optional, Tuple, cast

from django.db.models import Exists, OuterRef, QuerySet, Subquery

from training.models import chapters, progress, sections, trainings
import static_assets.models as models_static_assets


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


def from_slug(*, user_pk: int, training_slug: str,) -> Optional[Tuple[trainings.Training, bool]]:
    try:
        training = (
            _published()
            .annotate(
                favorited=Exists(
                    trainings.Favorite.objects.filter(user_id=user_pk, training_id=OuterRef('pk'))
                )
            )
            .prefetch_related('tags')
            .get(slug=training_slug)
        )
    except trainings.Training.DoesNotExist:
        return None

    return training, cast(bool, getattr(training, 'favorited'))


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
        .exclude(favorites__user_id=user_pk)
        .prefetch_related('tags')
        .order_by('-date_created')
    )


def navigation(
    *, user_pk: int, training_pk: int
) -> Tuple[trainings.Training, List[chapters.Chapter], List[sections.Section]]:
    return (
        _published().get(id=training_pk),
        list(chapters.Chapter.objects.filter(training_id=training_pk).all()),
        list(
            sections.Section.objects.annotate(
                started=Exists(
                    progress.UserSectionProgress.objects.filter(
                        user_id=user_pk, section_id=OuterRef('pk'), started=True
                    )
                ),
                finished=Exists(
                    progress.UserSectionProgress.objects.filter(
                        user_id=user_pk, section_id=OuterRef('pk'), finished=True
                    )
                ),
                video_position=Subquery(
                    models_static_assets.UserVideoProgress.objects.filter(
                        user_id=user_pk, video__static_asset__section=OuterRef('pk')
                    ).values('position')
                ),
                video_duration=Subquery(
                    models_static_assets.Video.objects.filter(
                        static_asset__section=OuterRef('pk')
                    ).values('duration')
                ),
            )
            .filter(chapter__training_id=training_pk)
            .all()
        ),
    )
