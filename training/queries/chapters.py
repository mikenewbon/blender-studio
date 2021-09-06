"""Handy queries related to training chapters."""
from typing import Optional, Tuple, cast

from django.db.models import Exists, OuterRef

from training.models import chapters, trainings


def from_slug(
    user_pk: int, training_slug: str, slug: str, **filters
) -> Optional[Tuple[trainings.Training, bool, chapters.Chapter]]:
    """Retrieve a training chapter by its slug."""
    try:
        chapter = (
            chapters.Chapter.objects.filter(**filters)
            .annotate(
                training_favorited=Exists(
                    trainings.Favorite.objects.filter(
                        user_id=user_pk, training_id=OuterRef('training_id')
                    )
                )
            )
            .select_related('training')
            .prefetch_related('sections', 'sections__static_asset', 'sections__static_asset__video')
            .get(training__slug=training_slug, slug=slug)
        )
    except chapters.Chapter.DoesNotExist:
        return None

    training = chapter.training
    training_favorited = cast(bool, getattr(chapter, 'training_favorited'))
    return training, training_favorited, chapter
