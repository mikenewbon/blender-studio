import datetime
from typing import Optional

import training.typed_templates.types
from training import typed_templates
from training.models import trainings, chapters, sections


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
    return typed_templates.types.Chapter(index=chapter.index, name=chapter.name, url=chapter.url)


def section_model_to_template_type(section: sections.Section,) -> typed_templates.types.Section:
    return typed_templates.types.Section(
        index=section.index, name=section.name, text=section.text, url=section.url
    )


def video_model_to_template_type(
    video: sections.Video, start_position: Optional[datetime.timedelta]
) -> typed_templates.types.Video:
    return typed_templates.types.Video(
        url=video.file.url,
        progress_url=video.progress_url,
        start_position=None if start_position is None else start_position.total_seconds(),
    )


def asset_model_to_template_type(asset: sections.Asset) -> typed_templates.types.Asset:
    return typed_templates.types.Asset(name=asset.file.name, url=asset.file.url)
