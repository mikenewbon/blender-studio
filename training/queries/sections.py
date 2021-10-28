# noqa: D100
import datetime
from typing import List, Optional, Tuple, cast

from django.db.models import Exists, OuterRef

from comments import models
from comments.queries import get_annotated_comments
from training.models import chapters, sections, trainings
import static_assets.models as models_static_assets


def recently_watched(*, user_pk: int) -> List[sections.Section]:  # noqa: D103
    return list(
        sections.Section.objects.raw(
            '''
            SELECT *
            FROM (SELECT s.*,
                         c.index AS chapter_index,
                         c.name AS chapter_name,
                         t.name AS training_name,
                         uvp.position AS video_position,
                         v.duration AS video_duration,
                         row_number()
                         OVER (
                            PARTITION BY t.id ORDER BY coalesce(uvp.date_updated, usp.date_updated)
                         DESC
                         ) AS row_number_per_training
                  FROM training_usersectionprogress usp
                           LEFT JOIN training_section s ON usp.section_id = s.id
                           LEFT JOIN training_chapter c ON s.chapter_id = c.id
                           LEFT JOIN training_training t ON c.training_id = t.id
                           LEFT JOIN static_assets_staticasset sa ON s.static_asset_id = sa.id
                           LEFT JOIN static_assets_video v ON sa.id = v.static_asset_id
                           LEFT JOIN static_assets_uservideoprogress uvp
                                ON v.id = uvp.video_id AND usp.user_id = uvp.user_id
                  WHERE usp.user_id = %s
                    AND usp.started
                    AND NOT usp.finished
                  ORDER BY coalesce(uvp.date_updated, usp.date_updated) DESC) progress
            WHERE progress.row_number_per_training = 1;
            ''',
            [user_pk],
        )
    )


def from_slug(  # noqa: D103
    *, user_pk: int, training_slug: str, section_slug: str, **filters
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
            sections.Section.objects.filter(**filters)
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
        _video = section.static_asset.video if section.static_asset else None
        progress_position = _video.get_progress_position(user_pk) if _video else None
        video = (_video, progress_position) if _video else None
    except models_static_assets.Video.DoesNotExist:
        video = None

    chapter = section.chapter
    training = chapter.training
    training_favorited = cast(bool, getattr(section, 'training_favorited'))
    comments = get_annotated_comments(section, user_pk)
    return training, training_favorited, chapter, section, video, comments
