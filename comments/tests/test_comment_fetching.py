from django.test.testcases import TestCase
from django.urls import reverse

from common.tests.factories.blog import RevisionFactory
from common.tests.factories.comments import CommentUnderPostFactory
from common.tests.factories.users import UserFactory


class TestCommentTreeConstruction(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.other_user = UserFactory()
        cls.post = RevisionFactory().post
        cls.post_url = reverse('post-detail', kwargs={'post_slug': cls.post.slug})

    def setUp(self) -> None:
        self.comment_no_replies = CommentUnderPostFactory(comment_post__post=self.post)
        self.comment_with_replies = CommentUnderPostFactory(comment_post__post=self.post)
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
        self.assertEqual(comment_trees[0].id, self.comment_with_replies.id)
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
