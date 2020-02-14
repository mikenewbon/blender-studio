from typing import Optional, Tuple, List

from django.db.models import QuerySet

from training_main.models import chapters, trainings, sections


def _published() -> 'QuerySet[sections.Section]':
    return sections.Section.objects.filter(
        chapter__training__status=trainings.TrainingStatus.published
    )


def from_slug(
    slug: str,
) -> Optional[
    Tuple[
        trainings.Training,
        chapters.Chapter,
        sections.Section,
        Optional[sections.Video],
        List[sections.Asset],
    ]
]:
    try:
        section = (
            _published()
            .select_related('chapter__training', 'chapter', 'video')
            .prefetch_related('assets')
            .get(slug=slug)
        )
        video = section.video
        assets = list(section.assets.all())
        chapter = section.chapter
        training = chapter.training
        return training, chapter, section, video, assets
    except sections.Section.DoesNotExist:
        return None
