# noqa: D100
import datetime
from typing import Dict, List, Literal, Optional, Union

from django.contrib.auth import get_user_model

from common import markdown
from common.types import assert_cast
from training import typed_templates
from training.models import chapters as chapters_models, sections as sections_models, trainings
from training.typed_templates.types import (
    ChapterNavigation,
    Navigation,
    SectionNavigation,
)
from training.typed_templates.home import RecentlyWatchedSection
import static_assets.models as models_static_assets

User = get_user_model()


def training_model_to_template_type(
    training: trainings.Training, favorited: bool
) -> typed_templates.types.Training:  # noqa: D103
    thumbnail_s_url = '' if not training.thumbnail_s_url else training.thumbnail_s_url
    thumbnail_m_url = '' if not training.thumbnail_m_url else training.thumbnail_m_url
    picture_header = '' if not training.picture_header else training.picture_header.url
    return typed_templates.types.Training(
        id=training.pk,
        name=training.name,
        description=training.description,
        summary=markdown.render(training.summary),
        type=trainings.TrainingType(training.type),
        difficulty=trainings.TrainingDifficulty(training.difficulty),
        tags=set(str(tag) for tag in training.tags.all()),
        url=training.url,
        admin_url=training.admin_url,
        favorite_url=training.favorite_url,
        date_updated=training.date_updated,
        favorited=favorited,
        thumbnail=thumbnail_s_url,
        thumbnail_s_url=thumbnail_s_url,
        thumbnail_m_url=thumbnail_m_url,
        picture_header=picture_header,
        is_free=training.is_free,
        flatpages=training.flatpages,
    )


def video_model_to_template_type(
    video: models_static_assets.Video, start_position: Optional[datetime.timedelta]
) -> typed_templates.types.Video:  # noqa: D103
    return typed_templates.types.Video(
        url=video.source.url,
        progress_url=video.progress_url,
        start_position=None if start_position is None else start_position.total_seconds(),
    )


def navigation_to_template_type(
    training: trainings.Training,
    chapters: List[chapters_models.Chapter],
    sections: List[sections_models.Section],
    *,
    user: User,
    current: Union[Literal['overview'], sections_models.Section],
) -> Navigation:  # noqa: D103
    sections_per_chapter: Dict[int, List[sections_models.Section]] = {}
    for section in sections:
        sections_per_chapter.setdefault(section.chapter_id, []).append(section)

    return Navigation(
        overview_url=training.url,
        overview_active=current == 'overview',
        training_admin_url=(
            training.admin_url
            if user.is_staff and user.has_perm('training.change_training')
            else None
        ),
        chapters=[
            ChapterNavigation(
                index=chapter.index,
                name=chapter.name,
                slug=chapter.slug,
                url=chapter.url,
                current=(
                    isinstance(current, sections_models.Section)
                    and any(
                        current.id == section.id
                        for section in sections_per_chapter.get(chapter.id, [])
                    )
                    or isinstance(current, chapters_models.Chapter)
                    and current.id == chapter.id
                ),
                admin_url=(
                    chapter.admin_url
                    if user.is_staff and user.has_perm('training.change_chapter')
                    else None
                ),
                is_published=assert_cast(bool, getattr(chapter, 'is_published')),
                sections=[
                    SectionNavigation(
                        index=section.index,
                        name=section.name,
                        url=section.url,
                        started=assert_cast(bool, getattr(section, 'started')),
                        finished=assert_cast(bool, getattr(section, 'finished')),
                        progress_fraction=(
                            0
                            if getattr(section, 'video_position') is None
                            or getattr(section, 'video_duration') is None
                            else getattr(section, 'video_position')
                            / getattr(section, 'video_duration')
                        ),
                        current=(
                            isinstance(current, sections_models.Section)
                            and current.id == section.id
                        ),
                        is_free=assert_cast(bool, getattr(section, 'is_free')),
                        is_featured=assert_cast(bool, getattr(section, 'is_featured')),
                        is_published=assert_cast(bool, getattr(section, 'is_published')),
                        source_type=section.static_asset.source_type
                        if getattr(section, 'static_asset', None)
                        else None,
                        admin_url=(
                            section.admin_url
                            if user.is_staff and user.has_perm('training.change_section')
                            else None
                        ),
                    )
                    for section in sorted(
                        sections_per_chapter.get(chapter.id, []), key=lambda s: s.index
                    )
                ],
            )
            for chapter in sorted(chapters, key=lambda c: c.index)
        ],
    )


def recently_watched_sections_to_template_type(
    recently_watched_sections: List[sections_models.Section],
) -> List[RecentlyWatchedSection]:
    """Return types Sections for use in templates."""
    return [
        RecentlyWatchedSection(
            index=section.index,
            name=section.name,
            url=section.url,
            training_name=getattr(section, 'training_name'),
            chapter_index=getattr(section, 'chapter_index'),
            chapter_name=getattr(section, 'chapter_name'),
            progress_fraction=(
                0
                if getattr(section, 'video_position') is None
                or getattr(section, 'video_duration') is None
                else getattr(section, 'video_position') / getattr(section, 'video_duration')
            ),
            thumbnail_s_url=section.thumbnail_s_url,
            thumbnail_m_url=section.thumbnail_m_url,
        )
        for section in recently_watched_sections
    ]
