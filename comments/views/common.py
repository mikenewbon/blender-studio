# noqa: D100
from typing import Dict, List, Optional, Sequence
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse

from comments import typed_templates
from comments.models import Comment
from common import markdown
from common.types import assert_cast

User = get_user_model()


def comments_to_template_type(
    comments: Sequence[Comment], comment_url: str, user: User
) -> typed_templates.Comments:
    # noqa: D103
    user_is_moderator = user.has_perm('comments.moderate_comment')
    lookup: Dict[Optional[int], List[Comment]] = {}
    # Sort all comments chronologically, oldest first
    for comment in sorted(comments, key=lambda c: c.date_created):
        reply_to_pk = None if comment.reply_to is None else comment.reply_to.pk

        lookup.setdefault(reply_to_pk, []).append(comment)

    def build_tree(comment: Comment) -> typed_templates.CommentTree:
        if comment.is_deleted:
            return build_deleted_tree(comment)
        # FIXME(anna) remove when all comments have message_html
        comment.message_html = comment.message_html or markdown.render(
            markdown.sanitize(comment.message)
        )
        return typed_templates.CommentTree(
            id=comment.pk,
            anchor=comment.anchor,
            full_name=comment.full_name or comment.username,
            date=comment.date_created,
            message=assert_cast(str, comment.message),
            message_html=assert_cast(str, comment.message_html),
            like_url=comment.like_url,
            liked=assert_cast(bool, getattr(comment, 'liked')),
            likes=assert_cast(int, getattr(comment, 'number_of_likes')),
            replies=[build_tree(reply) for reply in lookup.get(comment.pk, [])],
            profile_image_url=comment.profile_image_url,
            badges=comment.badges,
            edit_url=(
                comment.edit_url
                if assert_cast(bool, getattr(comment, 'owned_by_current_user'))
                else None
            ),
            admin_edit_url=comment.edit_url if user_is_moderator else None,
            archive_tree_url=comment.archive_tree_url if user_is_moderator else None,
            delete_url=(
                comment.delete_url
                if assert_cast(bool, getattr(comment, 'owned_by_current_user'))
                else None
            ),
            admin_delete_url=comment.delete_url if user_is_moderator else None,
            delete_tree_url=comment.delete_tree_url if user_is_moderator else None,
            hard_delete_tree_url=comment.hard_delete_tree_url if user_is_moderator else None,
            edited=(comment.date_updated != comment.date_created),
            is_archived=comment.is_archived,
            is_top_level=True if comment.reply_to is None else False,
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
            anchor=comment.anchor,
            date=comment.date_created,
            replies=[build_tree(reply) for reply in lookup.get(comment.pk, [])],
            is_archived=comment.is_archived,
            is_top_level=True if comment.reply_to is None else False,
        )

    # Top-level comments are ordered by number of likes and date
    top_level_comments = sorted(
        (comment for comment in lookup.get(None, [])),
        key=lambda c: (-c.number_of_likes, c.date_created),
    )

    return typed_templates.Comments(
        comment_url=comment_url,
        number_of_comments=len(comments),
        comment_trees=[build_tree(comment) for comment in top_level_comments],
        profile_image_url=user.image_url if getattr(user, 'image', None) else None,
    )


def comment_response(request, comment_model, to_field, field_pk):
    """Add a comment linked to a specific model and pk."""
    parsed_body = json.loads(request.body)

    reply_to_pk = int(parsed_body['reply_to']) if parsed_body.get('reply_to') else None
    message = assert_cast(str, parsed_body['message'])

    @transaction.atomic
    def create_comment(
        *, user_pk: int, message: str, reply_to_pk: Optional[int], **kwargs
    ) -> Comment:
        comment = Comment.objects.create(user_id=user_pk, message=message, reply_to_id=reply_to_pk)
        comment_model.objects.create(comment_id=comment.id, **kwargs)
        return comment

    m2m_params = {to_field: field_pk}
    comment = create_comment(
        user_pk=request.user.pk, message=message, reply_to_pk=reply_to_pk, **m2m_params
    )

    return JsonResponse(comment.to_dict())
