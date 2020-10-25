import datetime
from typing import List, Optional, Tuple, cast

from django.db.models import Exists, OuterRef, QuerySet

from comments import models
from comments.queries import get_annotated_comments
from training.models import chapters, sections, trainings
from static_assets.models.progress import UserVideoProgress
import static_assets.models as models_static_assets


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
                  FROM training_usersectionprogress usp
                           LEFT JOIN training_section s ON usp.section_id = s.id
                           LEFT JOIN training_chapter c ON s.chapter_id = c.id
                           LEFT JOIN training_training t ON c.training_id = t.id
                           LEFT JOIN static_assets_staticasset sa ON s.static_asset_id = sa.id
                           LEFT JOIN static_assets_video v ON sa.id = v.static_asset_id
                           LEFT JOIN static_assets_uservideoprogress uvp ON v.id = uvp.video_id AND usp.user_id = uvp.user_id
                  WHERE usp.user_id = %s
                    AND usp.started
                    AND NOT usp.finished
                  ORDER BY coalesce(uvp.date_updated, usp.date_updated) DESC) progress
            WHERE progress.row_number_per_training = 1;
            ''',
            [user_pk],
        )
    )


def from_slug(
    *, user_pk: int, training_slug: str, section_slug: str
) -> Optional[
    Tuple[
        trainings.Training,
        bool,
        chapters.Chapter,
        sections.Section,
        Optional[Tuple[models_static_assets.Video, Optional[datetime.timedelta]]],
        List[models.Comment],
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
            .prefetch_related('static_asset', 'comments', 'comments__user')
            .get(chapter__training__slug=training_slug, slug=section_slug)
        )
    except sections.Section.DoesNotExist:
        return None

    video: Optional[Tuple[models_static_assets.Video, Optional[datetime.timedelta]]]
    try:
        try:
            progress = section.static_asset.video.progress.get(user_id=user_pk)
        except UserVideoProgress.DoesNotExist:
            progress = None
        video = (section.static_asset.video, None if progress is None else progress.position)
    except models_static_assets.Video.DoesNotExist:
        video = None

    chapter = section.chapter
    training = chapter.training
    training_favorited = cast(bool, getattr(section, 'training_favorited'))
    comments = get_annotated_comments(section, user_pk)
    return training, training_favorited, chapter, section, video, comments


def comment(
    *, user_pk: int, section_pk: int, message: str, reply_to_pk: Optional[int]
) -> models.Comment:
    comment = models.Comment.objects.create(
        user_id=user_pk, message=message, reply_to_id=reply_to_pk
    )
    sections.SectionComment.objects.create(comment_id=comment.id, section_id=section_pk)
    return comment
