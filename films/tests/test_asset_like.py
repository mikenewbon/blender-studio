import json

from actstream.models import Action
from django.test import TestCase

from common.tests.factories.films import AssetFactory
from common.tests.factories.users import UserFactory


class TestAssetLikeEndpoint(TestCase):
    maxDiff = None

    def setUp(self):
        self.user = UserFactory()
        self.asset = AssetFactory(static_asset__author=self.user)
        self.client.force_login(self.user)

    def test_like_asset_increases_number_of_likes_by_one(self):
        self.assertEqual(self.asset.likes.count(), 0)
        response = self.client.post(
            self.asset.like_url,
            {'like': True},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {'like': True, 'number_of_likes': 1},
        )
        self.assertEqual(self.asset.likes.count(), 1)

        # One more like from a different user
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.post(
            self.asset.like_url,
            {'like': True},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {'like': True, 'number_of_likes': 2},
        )
        self.assertEqual(self.asset.likes.count(), 2)

        # Unlike the asset
        response = self.client.post(
            self.asset.like_url,
            {'like': False},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {'like': False, 'number_of_likes': 1},
        )
        self.assertEqual(self.asset.likes.count(), 1)

    def test_like_asset_does_not_create_a_notification_for_the_same_user(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        response = self.client.post(
            self.asset.like_url,
            {'like': True},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        # No activity still
        self.assertEqual(Action.objects.count(), 0)

    def test_like_asset_creates_a_notification(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        # Login as a new user
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.post(
            self.asset.like_url,
            {'like': True},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)

        action = Action.objects.first()
        asset_author = self.asset.static_asset.author or self.asset.static_asset.user
        # Asset's author should be notified about the like
        self.assertEqual(
            [str(_.action) for _ in asset_author.notifications.all()],
            [f'{user} liked {self.asset} 0 minutes ago'],
        )
        self.assertEqual(
            [str(_.action) for _ in asset_author.notifications_unread],
            [f'{user} liked {self.asset} 0 minutes ago'],
        )
        # TODO(anna): check notification endpoint too

        self.assertIsNone(action.action_object)
        self.assertEqual(action.actor, user)
        self.assertFalse(action.public)

    def test_like_asset_multiple_times_only_creates_one_notification(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        # Login as a new user
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.post(
            self.asset.like_url,
            {'like': True},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)

        action = Action.objects.first()
        # Asset's author should be notified about the like
        asset_author = self.asset.static_asset.author or self.asset.static_asset.user
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.asset.static_asset.author)],
            [f'{user} liked {self.asset} 0 minutes ago'],
        )
        self.assertEqual(
            [str(_.action) for _ in asset_author.notifications.all()],
            [f'{user} liked {self.asset} 0 minutes ago'],
        )
        self.assertEqual(
            [str(_.action) for _ in asset_author.notifications_unread],
            [f'{user} liked {self.asset} 0 minutes ago'],
        )

        # Unlike the post
        response = self.client.post(
            self.asset.like_url,
            {'like': False},
            content_type='application/json',
        )
        self.assertEqual(Action.objects.count(), 1)

        # Like it again
        response = self.client.post(
            self.asset.like_url,
            {'like': True},
            content_type='application/json',
        )
        self.assertEqual(Action.objects.count(), 1)

        self.assertIsNone(action.action_object)
        self.assertEqual(action.actor, user)
        self.assertFalse(action.public)
