from typing import Dict, List, Optional, Sequence

from comments import typed_templates
from comments.models import Comment
from common.types import assert_cast


def comments_to_template_type(
    comments: Sequence[Comment], comment_url: str, user_is_moderator: bool
) -> typed_templates.Comments:
    lookup: Dict[Optional[int], List[Comment]] = {}
    for comment in sorted(comments, key=lambda c: c.date_created, reverse=True):
        reply_to_pk = None if comment.reply_to is None else comment.reply_to.pk

        lookup.setdefault(reply_to_pk, []).append(comment)

    def build_tree(comment: Comment) -> typed_templates.CommentTree:
        if comment.is_deleted:
            return build_deleted_tree(comment)

        return typed_templates.CommentTree(
            id=comment.pk,
            full_name=comment.full_name,
            date=comment.date_created,
            message=assert_cast(str, comment.message),
            like_url=comment.like_url,
            liked=assert_cast(bool, getattr(comment, 'liked')),
            likes=assert_cast(int, getattr(comment, 'number_of_likes')),
            replies=[build_tree(reply) for reply in lookup.get(comment.pk, [])],
            profile_image_url='https://blender.chat/avatar/MikeNewbon',
            edit_url=(
                comment.edit_url
                if assert_cast(bool, getattr(comment, 'owned_by_current_user')) or user_is_moderator
                else None
            ),
            delete_url=(
                comment.delete_url
                if assert_cast(bool, getattr(comment, 'owned_by_current_user')) or user_is_moderator
                else None
            ),
            edited=(comment.date_updated != comment.date_created),
            is_archived=comment.is_archived,
        )

    def build_deleted_tree(comment: Comment) -> typed_templates.DeletedCommentTree:
        """
        Prepare comments marked as deleted to be displayed in the comment tree.

        Deleted comments with replies have to be kept in the database to preserve
        the integrity of the conversation, but their message and user should not
        be displayed. It should also be impossible to edit or delete them again.
        """
        return typed_templates.DeletedCommentTree(
            id=comment.pk,
            date=comment.date_created,
            replies=[build_tree(reply) for reply in lookup.get(comment.pk, [])],
            profile_image_url='https://blender.chat/avatar/MikeNewbon',
            # TODO(Natalia): set an empty profile picture in deleted comments
            is_archived=comment.is_archived,
        )

    return typed_templates.Comments(
        comment_url=comment_url,
        number_of_comments=len(comments),
        comment_trees=[build_tree(comment) for comment in lookup.get(None, [])],
        profile_image_url='https://blender.chat/avatar/fsiddi',
    )
