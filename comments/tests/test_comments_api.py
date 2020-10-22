from unittest.mock import ANY
import json
import logging

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
        cls.admin = UserFactory(is_superuser=True)

        # Do not show logs while running this test case (to avoid cluttering the test output)
        logging.disable(logging.ERROR)

    def setUp(self) -> None:
        self.comment_with_replies = CommentFactory(user=self.user)
        self.reply = CommentFactory(reply_to=self.comment_with_replies, user=self.other_user)
        self.comment_without_replies = CommentFactory(
            reply_to=self.comment_with_replies, user=self.user
        )
        self.client.force_login(self.user)

    def tearDown(self):
        # Restore logging configuration
        logging.disable(logging.NOTSET)

    def test_user_can_soft_delete_own_comment_without_replies(self):
        comment_pk = self.comment_without_replies.pk
        self.assertFalse(self.comment_without_replies.is_deleted)
        response = self.client.post(reverse('comment-delete', kwargs={'comment_pk': comment_pk}))

        self.assertEqual(response.status_code, 200)
        # Deleted comments are kept in the database, but marked as deleted.
        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertIsNotNone(comment.date_deleted)
        self.assertTrue(comment.is_deleted)

    def test_user_can_soft_delete_own_comment_with_replies(self):
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

    def test_admin_can_soft_delete_comment(self):
        self.client.force_login(self.admin)
        comment_pk = self.comment_without_replies.pk
        response = self.client.post(reverse('comment-delete', kwargs={'comment_pk': comment_pk}))

        self.assertEqual(response.status_code, 200)
        # Deleted comments are kept in the database, but marked as deleted.
        comment = Comment.objects.filter(pk=comment_pk).first()
        self.assertIsNotNone(comment)
        self.assertTrue(comment.is_deleted)


class TestCommentDeleteTreeEndpoints(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.admin = UserFactory(is_superuser=True)

        # Do not show warnings while running this test case (to avoid cluttering the test output)
        logging.disable(logging.ERROR)

    def setUp(self) -> None:
        # Create comment tree
        comment_base = CommentFactory()
        comment_should_stay, self.comment_to_delete = CommentFactory.create_batch(
            2, reply_to=comment_base, user=self.user,
        )
        reply_to_delete_0, reply_to_delete_1 = CommentFactory.create_batch(
            2, reply_to=self.comment_to_delete
        )
        reply_to_delete_2 = CommentFactory(reply_to=reply_to_delete_0)
        reply_to_delete_3 = CommentFactory(reply_to=reply_to_delete_2)
        self.tree_comments_should_stay = [comment_base, comment_should_stay]
        self.tree_comments_to_delete = [
            self.comment_to_delete,
            reply_to_delete_0,
            reply_to_delete_1,
            reply_to_delete_2,
            reply_to_delete_3,
        ]

        self.soft_delete_url = reverse(
            'comment-delete-tree', kwargs={'comment_pk': self.comment_to_delete.pk}
        )
        self.hard_delete_url = reverse(
            'comment-hard-delete-tree', kwargs={'comment_pk': self.comment_to_delete.pk}
        )

        self.client.force_login(self.user)

    def tearDown(self):
        # Restore logging configuration
        logging.disable(logging.NOTSET)

    def test_user_cannot_soft_delete_comments_tree(self):
        response = self.client.post(self.soft_delete_url)

        self.assertEqual(response.status_code, 403)
        self.comment_to_delete.refresh_from_db()
        self.assertFalse(self.comment_to_delete.is_deleted)

    def test_admin_can_soft_delete_comments_tree(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.soft_delete_url)

        self.assertEqual(response.status_code, 200)
        for c in self.tree_comments_should_stay:
            c.refresh_from_db()
            self.assertFalse(c.is_deleted)
        for c in self.tree_comments_to_delete:
            c.refresh_from_db()
            self.assertTrue(c.is_deleted)

    def test_user_cannot_hard_delete_comments_tree(self):
        comment_pk = self.comment_to_delete.pk
        response = self.client.post(self.hard_delete_url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=comment_pk).exists())
        self.comment_to_delete.refresh_from_db()
        self.assertFalse(self.comment_to_delete.is_deleted)

    def test_admin_can_hard_delete_comments_tree(self):
        self.client.force_login(self.admin)
        deleted_comments_pks = [c.pk for c in self.tree_comments_to_delete]
        response = self.client.post(self.hard_delete_url)

        self.assertEqual(response.status_code, 200)
        for c in self.tree_comments_should_stay:
            c.refresh_from_db()
            self.assertFalse(c.is_deleted)
        self.assertFalse(Comment.objects.filter(pk__in=deleted_comments_pks).exists())


class TestCommentArchiveTreeEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.admin = UserFactory(is_superuser=True)

    def setUp(self) -> None:
        self.comment = CommentFactory(user=self.user)
        self.archive_url = reverse('comment-archive-tree', kwargs={'comment_pk': self.comment.pk})

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
        self.comment.refresh_from_db()
        self.assertNotEqual(initial_state, self.comment.is_archived)

        response_2 = self.client.post(self.archive_url)
        self.assertEqual(initial_state, json.loads(response_2.content)['is_archived'])
        self.comment.refresh_from_db()
        self.assertEqual(initial_state, self.comment.is_archived)

    def test_entire_tree_is_archived(self):
        comment_0 = CommentFactory()
        reply_1_0, reply_1_1 = CommentFactory.create_batch(2, reply_to=comment_0)
        reply_2_0, reply_2_1 = CommentFactory.create_batch(2, reply_to=reply_1_0)
        reply_3_0 = CommentFactory(reply_to=reply_2_0)
        other_comment = CommentFactory()
        comment_tree_to_archive = [comment_0, reply_1_0, reply_1_1, reply_2_0, reply_2_1, reply_3_0]
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('comment-archive-tree', kwargs={'comment_pk': reply_2_0.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['is_archived'])
        for comment in comment_tree_to_archive:
            comment.refresh_from_db()
            self.assertTrue(comment.is_archived)
        self.assertFalse(other_comment.is_archived)


class TestCommentEditEndpoint(TestCase):
    maxDiff = None

    def setUp(self):
        self.user = UserFactory()
        self.comment = CommentFactory(user=self.user)
        self.edit_url = reverse('comment-edit', kwargs={'comment_pk': self.comment.pk})
        self.client.force_login(self.user)

    def test_edit_full_response(self):
        edit_message = '# Header\n**bold** _italic_'
        response = self.client.post(
            self.edit_url, {'message': edit_message}, content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                'date_string': ANY,
                'delete_url': f'/comments/api/comments/{self.comment.pk}/delete/',
                'edit_url': f'/comments/api/comments/{self.comment.pk}/edit/',
                'full_name': '',
                'id': self.comment.pk,
                'like_url': f'/comments/api/comments/{self.comment.pk}/like/',
                'liked': False,
                'likes': 0,
                'message': '# Header\n**bold** _italic_',
                'message_html': '<h1>Header</h1>\n'
                '<p><strong>bold</strong> <em>italic</em></p>\n',
                'profile_image_url': None,
            },
        )

    def test_edit_with_shortcodes(self):
        edit_message = '# Header\n**bold** _italic_ {youtube UbyxFZSZZ90}'
        response = self.client.post(
            self.edit_url, {'message': edit_message}, content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                'date_string': ANY,
                'delete_url': f'/comments/api/comments/{self.comment.pk}/delete/',
                'edit_url': f'/comments/api/comments/{self.comment.pk}/edit/',
                'full_name': '',
                'id': self.comment.pk,
                'like_url': f'/comments/api/comments/{self.comment.pk}/like/',
                'liked': False,
                'likes': 0,
                'message': edit_message,
                'message_html': '<h1>Header</h1>\n'
                '<p><strong>bold</strong> <em>italic</em> <div '
                'class="embed-responsive embed-responsive-16by9"><iframe '
                'class="shortcode youtube embed-responsive-item" width="560" '
                'height="315" '
                'src="https://www.youtube.com/embed/UbyxFZSZZ90?rel=0" '
                'frameborder="0" allow="autoplay; encrypted-media" '
                'allowfullscreen></iframe></div></p>\n',
                'profile_image_url': None,
            },
        )

    def test_edit_linkify_urlize(self):
        edit_message = '**bold** https://example.com'
        response = self.client.post(
            self.edit_url,
            {'message': edit_message},
            content_type='application/json',
        )

        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], edit_message)
        self.assertEqual(
            response_data['message_html'],
            '<p><strong>bold</strong> '
            '<a href="https://example.com">https://example.com</a></p>\n',
        )
