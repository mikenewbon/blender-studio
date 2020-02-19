from typing import Optional, Tuple, List, cast

from django.db.models import QuerySet, Exists, Subquery, OuterRef

from training_main.models import chapters, trainings, sections


def _published() -> 'QuerySet[chapters.Chapter]':
    return chapters.Chapter.objects.filter(training__status=trainings.TrainingStatus.published)


def from_slug_with_sections(
    *, user_pk: int, chapter_slug: str,
) -> Optional[Tuple[trainings.Training, bool, chapters.Chapter, List[sections.Section]]]:
    try:
        chapter = (
            _published()
            .annotate(
                training_favorited=Exists(
                    trainings.Favorite.objects.filter(
                        user_id=user_pk, training_id=OuterRef('training_id')
                    )
                )
            )
            .select_related('training')
            .get(slug=chapter_slug)
        )
    except chapters.Chapter.DoesNotExist:
        return None

    training = chapter.training
    training_favorited = cast(bool, getattr(chapter, 'training_favorited'))
    sections = list(chapter.sections.all())
    return training, training_favorited, chapter, sections
