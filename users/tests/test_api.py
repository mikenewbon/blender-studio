from django.test import TestCase
from django.urls import reverse

from common.tests.factories.blog import PostFactory
from common.tests.factories.comments import CommentUnderPostFactory
from common.tests.factories.users import UserFactory
from users.models import Notification


class TestNotificationMarkReadEndpoint(TestCase):
    maxDiff = None

    def setUp(self):
        self.user = UserFactory()
        post = PostFactory(author=self.user)
        post_comment = CommentUnderPostFactory(comment_post__post=post)
        ((_, action),) = post_comment.create_action()
        self.notification = action.notifications.first()

    def test_mark_notification_as_read_not_allowed_for_anonymous(self):
        self.assertIsNone(self.notification.date_read)

        response = self.client.post(self.notification.mark_read_url)

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.notification.date_read)

    def test_mark_notification_as_read_not_allowed_for_different_user(self):
        self.assertIsNone(self.notification.date_read)

        self.user = UserFactory()
        self.client.force_login(self.user)
        response = self.client.post(self.notification.mark_read_url)

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.notification.date_read)

    def test_mark_notification_as_read(self):
        self.assertIsNone(Notification.objects.get(id=self.notification.pk).date_read)

        self.client.force_login(self.user)
        response = self.client.post(self.notification.mark_read_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(Notification.objects.get(id=self.notification.pk).date_read)


class TestNotificationsMarkReadEndpoint(TestCase):
    maxDiff = None

    def setUp(self):
        self.user = UserFactory()
        post = PostFactory(author=self.user)
        post_comment = CommentUnderPostFactory(comment_post__post=post)
        ((_, action),) = post_comment.create_action()
        self.notification = action.notifications.first()
        self.mark_read_url = reverse('api-notifications-mark-read')

    def test_mark_notifications_as_read_not_allowed_for_anonymous(self):
        self.assertIsNone(self.notification.date_read)

        response = self.client.post(self.mark_read_url)

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.notification.date_read)

    def test_mark_notifications_as_read(self):
        self.assertIsNone(Notification.objects.get(id=self.notification.pk).date_read)

        self.client.force_login(self.user)
        response = self.client.post(self.mark_read_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(Notification.objects.get(id=self.notification.pk).date_read)
