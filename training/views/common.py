import datetime
from typing import Dict, List, Literal, Optional, Union

from django.contrib.auth.models import User

from common.types import assert_cast
from training import typed_templates
from training.models import chapters, sections as sections_models, trainings
from training.typed_templates.types import ChapterNavigation, Navigation, SectionNavigation


def training_model_to_template_type(
    training: trainings.Training, favorited: bool
) -> typed_templates.types.Training:
    return typed_templates.types.Training(
        name=training.name,
        description=training.description,
        summary=training.summary,
        type=trainings.TrainingType(training.type),
        difficulty=trainings.TrainingDifficulty(training.difficulty),
        tags=set(str(tag) for tag in training.tags.all()),
        url=training.url,
        favorite_url=training.favorite_url,
        date_updated=training.date_updated,
        favorited=favorited,
    )


def chapter_model_to_template_type(chapter: chapters.Chapter,) -> typed_templates.types.Chapter:
    return typed_templates.types.Chapter(index=chapter.index, name=chapter.name)


def section_model_to_template_type(
    section: sections_models.Section,
) -> typed_templates.types.Section:
    return typed_templates.types.Section(
        index=section.index, name=section.name, text=section.text, url=section.url
    )


def video_model_to_template_type(
    video: sections_models.Video, start_position: Optional[datetime.timedelta]
) -> typed_templates.types.Video:
    return typed_templates.types.Video(
        url=video.file.url,
        progress_url=video.progress_url,
        start_position=None if start_position is None else start_position.total_seconds(),
    )


def asset_model_to_template_type(asset: sections_models.Asset) -> typed_templates.types.Asset:
    return typed_templates.types.Asset(name=asset.file.name, url=asset.file.url)


def navigation_to_template_type(
    training: trainings.Training,
    chapters: List[chapters.Chapter],
    sections: List[sections_models.Section],
    *,
    user: User,
    current: Union[Literal['overview'], sections_models.Section],
) -> Navigation:
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
                current=(
                    isinstance(current, sections_models.Section)
                    and any(
                        current.id == section.id
                        for section in sections_per_chapter.get(chapter.id, [])
                    )
                ),
                admin_url=(
                    chapter.admin_url
                    if user.is_staff and user.has_perm('training.change_chapter')
                    else None
                ),
                sections=[
                    SectionNavigation(
                        index=section.index,
                        name=section.name,
                        url=section.url,
                        started=assert_cast(bool, getattr(section, 'started')),
                        finished=assert_cast(bool, getattr(section, 'finished')),
                        progress_fraction=(
                            0.5
                            if getattr(section, 'video_position') is None
                            or getattr(section, 'video_duration') is None
                            else getattr(section, 'video_position')
                            / getattr(section, 'video_duration')
                        ),
                        current=(
                            isinstance(current, sections_models.Section)
                            and current.id == section.id
                        ),
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
