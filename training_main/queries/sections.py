import datetime
from typing import Optional, Tuple, List, cast

from django.db.models import QuerySet, Exists, OuterRef
from django.db.models.aggregates import Count

from training_main.models import chapters, trainings, sections, comments
from training_main.models.comments import Like
from training_main.models.progress import UserVideoProgress


def _published() -> 'QuerySet[sections.Section]':
    return sections.Section.objects.filter(
        chapter__training__status=trainings.TrainingStatus.published
    )


def recently_watched(*, user_pk: int) -> List[sections.Section]:
    return list(
        sections.Section.objects.raw(
            '''
            SELECT *
            FROM (SELECT s.*,
                         c.index                                                                             AS chapter_index,
                         c.name                                                                              AS chapter_name,
                         t.name                                                                              AS training_name,
                         uvp.position                                                                        AS video_position,
                         v.duration                                                                          AS video_duration,
                         row_number()
                         OVER (PARTITION BY t.id ORDER BY coalesce(uvp.date_updated, usp.date_updated) DESC) AS row_number_per_training
                  FROM training_main_usersectionprogress usp
                           LEFT JOIN training_main_section s ON usp.section_id = s.id
                           LEFT JOIN training_main_chapter c ON s.chapter_id = c.id
                           LEFT JOIN training_main_training t ON c.training_id = t.id
                           LEFT JOIN training_main_video v ON s.id = v.section_id
                           LEFT JOIN training_main_uservideoprogress uvp ON v.id = uvp.video_id AND usp.user_id = uvp.user_id
                  WHERE usp.user_id = 1
                    AND usp.started
                    AND NOT usp.finished
                  ORDER BY coalesce(uvp.date_updated, usp.date_updated) DESC) progress
            WHERE progress.row_number_per_training = 1;
            '''
        )
    )


def from_slug(
    *, user_pk: int, section_slug: str,
) -> Optional[
    Tuple[
        trainings.Training,
        bool,
        chapters.Chapter,
        sections.Section,
        Optional[Tuple[sections.Video, Optional[datetime.timedelta]]],
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

    video: Optional[Tuple[sections.Video, Optional[datetime.timedelta]]]
    try:
        try:
            progress = section.video.progress.get(user_id=user_pk)
        except UserVideoProgress.DoesNotExist:
            progress = None
        video = (section.video, None if progress is None else progress.position)
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


def video_from_pk(*, video_pk: int) -> sections.Video:
    return sections.Video.objects.get(pk=video_pk)
