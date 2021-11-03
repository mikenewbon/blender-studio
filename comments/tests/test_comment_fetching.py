from unittest.mock import patch, Mock

from django.test.testcases import TestCase
from django.urls import reverse

from comments.models import Like
from comments.queries import get_annotated_comments, set_comment_like
from common.tests.factories.blog import PostFactory
from common.tests.factories.comments import CommentUnderPostFactory
from common.tests.factories.users import UserFactory


@patch('sorl.thumbnail.base.ThumbnailBackend.get_thumbnail', Mock(url=''))
class TestCommentTreeConstruction(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.other_user = UserFactory()
        cls.post = PostFactory()
        cls.post_url = reverse('post-detail', kwargs={'slug': cls.post.slug})

    def setUp(self) -> None:
        self.comment_with_replies = CommentUnderPostFactory(comment_post__post=self.post)
        self.comment_no_replies = CommentUnderPostFactory(comment_post__post=self.post)
        self.reply_1 = CommentUnderPostFactory(
            comment_post__post=self.post, reply_to=self.comment_with_replies
        )
        self.reply_2 = CommentUnderPostFactory(
            comment_post__post=self.post, reply_to=self.comment_with_replies
        )

    def test_deleted_comments_with_replies_are_kept_in_tree(self):
        self.comment_with_replies.soft_delete()
        response = self.client.get(self.post_url)

        self.assertEqual(response.status_code, 200)
        comment_trees = response.context['comments'].comment_trees
        self.assertEqual(len(comment_trees), 2)
        self.assertEqual(
            comment_trees[0].id, self.comment_with_replies.id, [str(_) for _ in comment_trees]
        )
        self.assertEqual(comment_trees[0].message, '[deleted]')
        self.assertEqual(len(comment_trees[0].replies), 2)

    def test_deleted_comments_without_replies_are_not_included_in_tree(self):
        self.comment_no_replies.soft_delete()
        response = self.client.get(self.post_url)

        self.assertEqual(response.status_code, 200)
        comment_trees = response.context['comments'].comment_trees
        self.assertEqual(len(comment_trees), 1)
        self.assertEqual(comment_trees[0].id, self.comment_with_replies.id)
        self.assertEqual(len(comment_trees[0].replies), 2)

    def test_deleted_comments_with_deleted_replies_not_included_in_tree(self):
        self.comment_with_replies.soft_delete_tree()
        response = self.client.get(self.post_url)

        self.assertEqual(response.status_code, 200)
        comment_trees = response.context['comments'].comment_trees
        self.assertEqual(len(comment_trees), 1)
        self.assertEqual(comment_trees[0].id, self.comment_no_replies.id)

    def test_get_annotated_comments_returns_correct_like_count(self):
        comment = CommentUnderPostFactory(comment_post__post=self.post)
        post = comment.post.all()[0]
        set_comment_like(comment_pk=post.comments.all()[0].pk, user_pk=self.user.pk, like=True)

        annotated_comments = get_annotated_comments(post, user_pk=self.user.pk)

        self.assertEqual(annotated_comments[0].likes.count(), 1)
        self.assertEqual(annotated_comments[0].number_of_likes, 1)

    def test_get_annotated_comments_returns_correct_like_count_even_if_user_deleted(self):
        comment = CommentUnderPostFactory(comment_post__post=self.post)
        post = comment.post.all()[0]
        set_comment_like(comment_pk=post.comments.all()[0].pk, user_pk=self.user.pk, like=True)

        annotated_comments = get_annotated_comments(post, user_pk=self.user.pk)

        self.assertEqual(annotated_comments[0].number_of_likes, 1)
        self.assertEqual(
            annotated_comments[0].number_of_likes,
            Like.objects.filter(comment_id=annotated_comments[0].pk).count(),
        )

        # After the user has been deleted, the likes count should still be the same
        user_pk = self.user.pk
        self.user.delete()

        annotated_comments = get_annotated_comments(post, user_pk=user_pk)

        self.assertEqual(annotated_comments[0].number_of_likes, 1)
        self.assertEqual(
            annotated_comments[0].number_of_likes,
            Like.objects.filter(comment_id=annotated_comments[0].pk).count(),
        )
