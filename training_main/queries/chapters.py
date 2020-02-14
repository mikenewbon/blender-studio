from typing import Optional, Tuple, List

from django.db.models import QuerySet

from training_main.models import chapters, trainings, sections


def _published() -> 'QuerySet[chapters.Chapter]':
    return chapters.Chapter.objects.filter(training__status=trainings.TrainingStatus.published)


def from_slug_with_sections(
    slug: str,
) -> Optional[Tuple[trainings.Training, chapters.Chapter, List[sections.Section]]]:
    try:
        chapter = _published().select_related('training').get(slug=slug)
        training = chapter.training
        sections = list(chapter.sections.all())
        return training, chapter, sections
    except chapters.Chapter.DoesNotExist:
        return None
