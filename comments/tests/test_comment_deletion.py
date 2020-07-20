from django.test import TestCase
from django.urls import reverse

from comments.models import Comment
from common.tests.factories.comments import CommentFactory
from common.tests.factories.users import UserFactory


class TestCommentDeletion(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.other_user = UserFactory()

    def setUp(self) -> None:
        self.comment_with_replies = CommentFactory(user=self.user)
        self.reply = CommentFactory(reply_to=self.comment_with_replies, user=self.other_user)
        self.comment_without_replies = CommentFactory(
            reply_to=self.comment_with_replies, user=self.user
        )
        self.client.force_login(self.user)

    def test_user_can_delete_own_comment_without_replies(self):
        comment_pk = self.comment_without_replies.pk
        response = self.client.post(reverse('comment_delete', kwargs={'comment_pk': comment_pk}))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Comment.objects.filter(pk=comment_pk).first())

    def test_comment_with_replies_is_not_deleted(self):
        comment_pk = self.comment_with_replies.pk
        response = self.client.post(reverse('comment_delete', kwargs={'comment_pk': comment_pk}))

        self.assertEqual(response.status_code, 200)
        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertIsNotNone(comment.date_deleted)
        self.assertTrue(comment.is_deleted)

    def test_user_cannot_delete_another_user_comment(self):
        comment_pk = self.reply.pk
        with self.assertRaises(Comment.DoesNotExist):
            self.client.post(reverse('comment_delete', kwargs={'comment_pk': comment_pk}))

        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertFalse(comment.is_deleted)
