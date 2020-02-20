from typing import Optional, Tuple, List, cast

from django.db.models import QuerySet, Exists, OuterRef

from training_main.models import chapters, trainings, sections, comments


def _published() -> 'QuerySet[sections.Section]':
    return sections.Section.objects.filter(
        chapter__training__status=trainings.TrainingStatus.published
    )


def from_slug(
    *, user_pk: int, section_slug: str,
) -> Optional[
    Tuple[
        trainings.Training,
        bool,
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
            .annotate(
                training_favorited=Exists(
                    trainings.Favorite.objects.filter(
                        user_id=user_pk, training_id=OuterRef('chapter__training_id')
                    )
                )
            )
            .select_related('chapter__training', 'chapter')
            .prefetch_related('video', 'assets', 'comments', 'comments__user')
            .get(slug=section_slug)
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
    training_favorited = cast(bool, getattr(section, 'training_favorited'))
    comments = list(section.comments.all())
    return training, training_favorited, chapter, section, video, assets, comments


def comment(
    *, user_pk: int, section_pk: int, message: str, reply_to_pk: Optional[int]
) -> comments.Comment:
    return comments.Comment.objects.create(
        user_id=user_pk, section_id=section_pk, message=message, reply_to_id=reply_to_pk
    )
