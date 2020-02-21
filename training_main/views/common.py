import datetime
from typing import Sequence, List, Optional, Dict, Type, TypeVar

import training_main.responses.common
from training_main.models import trainings, chapters, sections
from training_main.models.comments import Comment

T = TypeVar('T', bound=object)


def assert_cast(typ: Type[T], val: object) -> T:
    assert isinstance(val, typ)
    return val


def training_model_to_template_type(
    training: trainings.Training, favorited: bool
) -> training_main.responses.common.Training:
    return training_main.responses.common.Training(
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


def chapter_model_to_template_type(
    chapter: chapters.Chapter,
) -> training_main.responses.common.Chapter:
    return training_main.responses.common.Chapter(
        index=chapter.index, name=chapter.name, url=chapter.url
    )


def section_model_to_template_type(
    section: sections.Section,
) -> training_main.responses.common.Section:
    return training_main.responses.common.Section(
        index=section.index, name=section.name, text=section.text, url=section.url
    )


def video_model_to_template_type(
    video: sections.Video, start_position: Optional[datetime.timedelta]
) -> training_main.responses.common.Video:
    return training_main.responses.common.Video(
        url=video.file.url,
        progress_url=video.progress_url,
        start_position=None if start_position is None else start_position.total_seconds(),
    )


def asset_model_to_template_type(asset: sections.Asset) -> training_main.responses.common.Asset:
    return training_main.responses.common.Asset(name=asset.file.name, url=asset.file.url)


def comments_to_template_type(
    comments: Sequence[Comment], comment_url: str,
) -> training_main.responses.common.Comments:
    lookup: Dict[Optional[int], List[Comment]] = {}
    for comment in sorted(comments, key=lambda c: c.date_created, reverse=True):
        reply_to_pk = None if comment.reply_to is None else comment.reply_to.pk

        lookup.setdefault(reply_to_pk, []).append(comment)

    def build_tree(comment: Comment) -> training_main.responses.common.CommentTree:
        return training_main.responses.common.CommentTree(
            id=comment.pk,
            username=comment.username,
            date=comment.date_created,
            message=comment.message,
            like_url=comment.like_url,
            liked=assert_cast(bool, getattr(comment, 'liked')),
            likes=assert_cast(int, getattr(comment, 'number_of_likes')),
            replies=[build_tree(reply) for reply in lookup.get(comment.pk, [])],
            profile_image_url='https://blender.chat/avatar/MikeNewbon',
        )

    return training_main.responses.common.Comments(
        comment_url=comment_url,
        number_of_comments=len(comments),
        comment_trees=[build_tree(comment) for comment in lookup.get(None, [])],
        profile_image_url='https://blender.chat/avatar/fsiddi',
    )
