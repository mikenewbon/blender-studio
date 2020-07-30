import json

from django.test import TestCase
from django.urls import reverse

from comments.models import Comment
from common.tests.factories.comments import CommentFactory
from common.tests.factories.users import UserFactory


class TestCommentDeleteEndpoint(TestCase):
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
        self.assertFalse(self.comment_without_replies.is_deleted)
        response = self.client.post(reverse('comment-delete', kwargs={'comment_pk': comment_pk}))

        self.assertEqual(response.status_code, 200)
        # Deleted comments are kept in the database, but marked as deleted.
        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertIsNotNone(comment.date_deleted)
        self.assertTrue(comment.is_deleted)

    def test_user_can_delete_own_comment_with_replies(self):
        comment_pk = self.comment_with_replies.pk
        response = self.client.post(reverse('comment-delete', kwargs={'comment_pk': comment_pk}))

        self.assertEqual(response.status_code, 200)
        # Deleted comments are kept in the database, but marked as deleted.
        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertIsNotNone(comment.date_deleted)
        self.assertTrue(comment.is_deleted)

    def test_user_cannot_delete_another_user_comment(self):
        comment_pk = self.reply.pk
        with self.assertRaises(Comment.DoesNotExist):
            self.client.post(reverse('comment-delete', kwargs={'comment_pk': comment_pk}))

        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertFalse(comment.is_deleted)


class TestCommentArchiveEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.admin = UserFactory(is_superuser=True)

    def setUp(self) -> None:
        self.comment = CommentFactory(user=self.user)
        self.archive_url = reverse('comment-archive', kwargs={'comment_pk': self.comment.pk})

    def test_regular_user_cannot_archive_comment(self):
        self.client.force_login(self.user)
        self.assertFalse(self.comment.is_archived)
        response = self.client.post(self.archive_url)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.comment.is_archived)

    def test_admin_can_archive_comment(self):
        self.client.force_login(self.admin)
        self.assertFalse(self.comment.is_archived)
        response = self.client.post(self.archive_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['is_archived'])
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_archived)

    def test_is_archived_flag_is_flipped_with_each_request(self):
        self.client.force_login(self.admin)
        initial_state = self.comment.is_archived

        response_1 = self.client.post(self.archive_url)
        self.assertNotEqual(initial_state, json.loads(response_1.content)['is_archived'])

        response_2 = self.client.post(self.archive_url)
        self.assertEqual(initial_state, json.loads(response_2.content)['is_archived'])
