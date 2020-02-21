from typing import Optional, Tuple, List, cast

from django.db.models import QuerySet, Exists, OuterRef
from django.db.models.aggregates import Count

from training_main.models import chapters, trainings, sections, comments
from training_main.models.comments import Like


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
    comments = list(
        section.comments.annotate(
            liked=Exists(Like.objects.filter(comment_id=OuterRef('pk'), user_id=user_pk)),
            number_of_likes=Count('likes'),
        ).all()
    )
    return training, training_favorited, chapter, section, video, assets, comments


def comment(
    *, user_pk: int, section_pk: int, message: str, reply_to_pk: Optional[int]
) -> comments.Comment:
    return comments.Comment.objects.create(
        user_id=user_pk, section_id=section_pk, message=message, reply_to_id=reply_to_pk
    )


def set_comment_like(*, comment_pk: int, user_pk: int, like: bool) -> int:
    if like:
        comments.Like.objects.update_or_create(
            comment_id=comment_pk, user_id=user_pk,
        )
    else:
        comments.Like.objects.filter(comment_id=comment_pk, user_id=user_pk).delete()

    return comments.Like.objects.filter(comment_id=comment_pk).count()
