from django.test import TestCase
from django.urls import reverse

from actstream.models import Action
from comments.models import Comment
from common.tests.factories.comments import CommentUnderSectionFactory
from common.tests.factories.training import SectionFactory
from common.tests.factories.users import UserFactory


class TestSectionComments(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.section = SectionFactory(user=self.other_user)
        self.section_comment_url = reverse(
            'section-comment', kwargs={'section_pk': self.section.pk}
        )
        self.section_comment = CommentUnderSectionFactory(
            comment_section__section=self.section, user=UserFactory()
        )

    def test_reply_to_comment_creates_notifications(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        data = {'message': 'Comment message', 'reply_to': self.section_comment.pk}
        response = self.client.post(self.section_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 2)

        # No notifications for the user who replied to the comment
        self.assertEqual(list(Action.objects.notifications(self.user)), [], self.user)
        self.assertEqual(list(self.user.notifications.all()), [], self.user)
        self.assertEqual(list(self.user.notifications_unread), [], self.user)
        # A notification for the author of the comment they replied to
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.section_comment.user)],
            [f'{self.user} replied to {self.section_comment} on {self.section} 0 minutes ago'],
            self.section_comment.user,
        )
        # A notification for the author of the training section
        comment = Comment.objects.get(pk=response.json()['id'])
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.section.user)],
            [f'{self.user} commented {comment} on {self.section} 0 minutes ago'],
        )
        self.assertEqual(
            [str(_.action) for _ in self.section.user.notifications_unread],
            [f'{self.user} commented {comment} on {self.section} 0 minutes ago'],
        )

    def test_reply_to_your_own_comment_does_not_create_notification(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.section_comment.user)
        data = {'message': 'Comment message', 'reply_to': self.section_comment.pk}
        response = self.client.post(self.section_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)

        comment = Comment.objects.get(pk=response.json()['id'])
        # No notifications for the user who replied to the comment
        self.assertEqual(list(Action.objects.notifications(self.section_comment.user)), [])
        # A notification for the author of the training section
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.section.user)],
            [f'{self.section_comment.user} commented {comment} on {self.section} 0 minutes ago'],
        )

    def test_liking_section_comment_creates_notification_for_comments_author(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        response = self.client.post(
            self.section_comment.like_url, {'like': True}, content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)
        action = Action.objects.first()
        self.assertEqual(action.action_object, self.section_comment)
        self.assertEqual(action.actor, self.user)
        self.assertEqual(action.target, self.section)
        self.assertFalse(action.public)

        self.assertNotEqual(self.section.user, self.section_comment.user)
        # Comment's author should be notified about the like on their comment
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.section_comment.user)],
            [f'{self.user} liked {self.section_comment} on {self.section} 0 minutes ago'],
        )
        self.assertEqual(
            [str(_.action) for _ in self.section_comment.user.notifications_unread],
            [f'{self.user} liked {self.section_comment} on {self.section} 0 minutes ago'],
        )
        # but training section's author should not be notified
        self.assertEqual(
            list(Action.objects.notifications(self.section.user)),
            [],
            self.section.user,
        )

    def test_commenting_on_section_creates_notification_for_sections_author(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        data = {'message': 'Comment message'}
        response = self.client.post(self.section_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)
        action = Action.objects.first()
        comment = Comment.objects.get(pk=response.json()['id'])
        self.assertEqual(action.actor, self.user)
        self.assertEqual(action.target, self.section)
        self.assertEqual(action.action_object, comment)
        self.assertEqual(
            str(action),
            f'{self.user} commented {comment} on {self.section} 0 minutes ago',
            str(action),
        )

        self.assertNotEqual(self.section.user, self.section_comment.user)
        # Section's author should be notified about the comment on their section
        self.assertEqual(list(Action.objects.notifications(self.section.user)), [action])
        self.assertEqual(list(Action.objects.notifications(self.section_comment.user)), [])
