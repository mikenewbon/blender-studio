from typing import Optional, Tuple, List

from django.db.models import QuerySet

from training_main.models import chapters, trainings, sections, comments


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
        List[comments.Comment],
    ]
]:
    try:
        section = (
            _published()
            .select_related('chapter__training', 'chapter')
            .prefetch_related('video', 'assets', 'comments', 'comments__user')
            .get(slug=slug)
        )
    except sections.Section.DoesNotExist:
        return None

    video: Optional[sections.Video]
    try:
        video = section.video
    except sections.Video.DoesNotExist:
        video = None
    assets = list(section.assets.all())
    chapter = section.chapter
    training = chapter.training
    comments = list(section.comments.all())
    return training, chapter, section, video, assets, comments
