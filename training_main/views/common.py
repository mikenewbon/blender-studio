from typing import Sequence, List, Optional, Dict

from training_main import responses
from training_main.models import trainings, chapters, sections
from training_main.models.comments import Comment


def training_model_to_template_type(training: trainings.Training) -> responses.types.Training:
    return responses.types.Training(
        name=training.name,
        description=training.description,
        summary=training.summary,
        type=trainings.TrainingType(training.type),
        difficulty=trainings.TrainingDifficulty(training.difficulty),
        tags=set(str(tag) for tag in training.tags.all()),
        url=training.url,
        date_updated=training.date_updated,
    )


def chapter_model_to_template_type(chapter: chapters.Chapter) -> responses.types.Chapter:
    return responses.types.Chapter(index=chapter.index, name=chapter.name, url=chapter.url)


def section_model_to_template_type(section: sections.Section) -> responses.types.Section:
    return responses.types.Section(
        index=section.index, name=section.name, text=section.text, url=section.url
    )


def video_model_to_template_type(video: sections.Video) -> responses.types.Video:
    return responses.types.Video(url=video.file.url)


def asset_model_to_template_type(asset: sections.Asset) -> responses.types.Asset:
    return responses.types.Asset(name=asset.file.name, url=asset.file.url)


def comments_to_comment_trees(comments: Sequence[Comment]) -> List[responses.types.CommentTree]:
    lookup: Dict[Optional[int], List[Comment]] = {}
    for comment in comments:
        reply_to_pk = None if comment.reply_to is None else comment.reply_to.pk

        lookup.setdefault(reply_to_pk, []).append(comment)

    def build_tree(comment: Comment) -> responses.types.CommentTree:
        return responses.types.CommentTree(
            username=comment.username,
            date_updated=comment.date_updated,
            message=comment.message,
            likes=comment.likes.count(),
            replies=[build_tree(reply) for reply in lookup.get(comment.pk, [])],
        )

    return [build_tree(comment) for comment in lookup.get(None, [])]
