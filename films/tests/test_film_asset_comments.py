from django.test import TestCase
from django.urls import reverse

from actstream.models import Action
from comments.models import Comment
from common.tests.factories.comments import CommentUnderAssetFactory
from common.tests.factories.films import AssetFactory
from common.tests.factories.users import UserFactory
from django.contrib.auth.models import Group

from users.models import Notification


class TestAssetComments(TestCase):
    def setUp(self):
        self.user_without_subscription = UserFactory()
        self.user = UserFactory()
        self.other_user = UserFactory()

        self.asset = AssetFactory()
        self.asset_comment_url = reverse('api-asset-comment', kwargs={'asset_pk': self.asset.pk})
        self.asset_comment = CommentUnderAssetFactory(comment_asset__asset=self.asset)

        # Commenting without subscription is not allowed, so add these to the right group
        subscribers, _ = Group.objects.get_or_create(name='subscriber')
        self.user.groups.add(subscribers)
        self.other_user.groups.add(subscribers)
        self.asset_comment.user.groups.add(subscribers)

    def test_comment_not_allowed_without_subscription(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user_without_subscription)
        data = {'message': 'Comment message'}
        response = self.client.post(self.asset_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 403)

    def test_reply_to_comment_not_allowed_without_subscription(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user_without_subscription)
        data = {'message': 'Comment message', 'reply_to': self.asset_comment.pk}
        response = self.client.post(self.asset_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 403)

    def test_reply_to_comment_creates_notifications(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        data = {'message': 'Comment message', 'reply_to': self.asset_comment.pk}
        response = self.client.post(self.asset_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 2)

        # No notifications for the user who replied to the comment
        self.assertEqual(list(Action.objects.notifications(self.user)), [], self.user)
        # A notification for the author of the comment they replied to
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.asset_comment.user)],
            [f'{self.user} replied to {self.asset_comment} on {self.asset} 0 minutes ago'],
            self.asset_comment.user,
        )
        # A notification for the author of the film asset
        asset_author = self.asset.static_asset.author or self.asset.static_asset.user
        comment = Comment.objects.get(pk=response.json()['id'])
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(asset_author)],
            [f'{self.user} commented {comment} on {self.asset} 0 minutes ago'],
        )

    def test_reply_to_your_own_comment_does_not_create_notification(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.asset_comment.user)
        data = {'message': 'Comment message', 'reply_to': self.asset_comment.pk}
        response = self.client.post(self.asset_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)

        comment = Comment.objects.get(pk=response.json()['id'])
        # No notifications for the user who replied to the comment
        self.assertEqual(list(Action.objects.notifications(self.asset_comment.user)), [])
        # A notification for the author of the film asset
        asset_author = self.asset.static_asset.author or self.asset.static_asset.user
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(asset_author)],
            [f'{self.asset_comment.user} commented {comment} on {self.asset} 0 minutes ago'],
        )

    def test_liking_asset_comment_creates_notification_for_comments_author(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        response = self.client.post(
            self.asset_comment.like_url, {'like': True}, content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)
        action = Action.objects.first()
        self.assertEqual(action.action_object, self.asset_comment)
        self.assertEqual(action.actor, self.user)
        self.assertEqual(action.target, self.asset)
        self.assertFalse(action.public)

        self.assertNotEqual(self.asset.static_asset.author, self.asset_comment.user)
        # Comment's author should be notified about the like on their comment
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.asset_comment.user)],
            [f'{self.user} liked {self.asset_comment} on {self.asset} 0 minutes ago'],
        )
        # but film asset's author should not be notified
        self.assertEqual(
            list(Action.objects.notifications(self.asset.static_asset.author)),
            [],
            self.asset.static_asset.author,
        )

    def test_commenting_on_asset_creates_notification_for_assets_author(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        data = {'message': 'Comment message'}
        response = self.client.post(self.asset_comment_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        action = Action.objects.first()
        comment = Comment.objects.get(pk=response.json()['id'])
        self.assertEqual(action.actor, self.user)
        self.assertEqual(action.target, self.asset)
        self.assertEqual(action.action_object, comment)
        self.assertEqual(
            str(action),
            f'{self.user} commented {comment} on {self.asset} 0 minutes ago',
            str(action),
        )

        asset_author = self.asset.static_asset.author or self.asset.static_asset.user
        self.assertIsNotNone(asset_author)
        self.assertNotEqual(asset_author, self.asset_comment.user)
        # Film asset's author should be notified about the comment on their asset
        self.assertEqual(Notification.objects.first().user, asset_author)
        self.assertEqual(list(Action.objects.notifications(asset_author)), [action])
        self.assertEqual(list(Action.objects.notifications(self.asset_comment.user)), [])
