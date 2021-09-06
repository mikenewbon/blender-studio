from typing import List, Optional, Tuple, cast

from django.db.models import Exists, OuterRef, Subquery

from training.models import chapters, progress, sections, trainings
import static_assets.models as models_static_assets


def set_favorite(*, training_pk: int, user_pk: int, favorite: bool) -> None:
    if favorite:
        trainings.Favorite.objects.filter(
            training__is_published=True
        ).update_or_create(
            training_id=training_pk, user_id=user_pk,
        )
    else:
        trainings.Favorite.objects.filter(
            training__is_published=True,
            training_id=training_pk,
            user_id=user_pk,
        ).delete()


def from_slug(
    *, user_pk: int, training_slug: str, **filters
) -> Optional[Tuple[trainings.Training, bool]]:
    try:
        training = (
            trainings.Training.objects.filter(**filters)
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


def favorited(*, user_pk: int, **filters) -> List[trainings.Training]:
    return list(
        trainings.Training.objects.filter(**filters)
        .prefetch_related('tags')
        .filter(favorites__user_id=user_pk)
        .order_by('-favorites__date_created')
    )


def all(user_pk: Optional[int], **filters) -> List[trainings.Training]:
    return list(
        trainings.Training.objects.filter(**filters)
        .exclude(favorites__user_id=user_pk)
        .prefetch_related('tags')
        .order_by('-date_created')
    )


def navigation(
    *, user_pk: int, training_pk: int, **filters
) -> Tuple[trainings.Training, List[chapters.Chapter], List[sections.Section]]:
    return (
        trainings.Training.objects.filter(**filters).get(id=training_pk),
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
