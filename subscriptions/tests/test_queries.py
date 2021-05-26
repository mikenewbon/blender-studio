from django.test import TestCase

from common.tests.factories.users import UserFactory
from common.tests.factories.subscriptions import SubscriptionFactory, TeamFactory

import looper.models

from subscriptions.queries import has_active_subscription


class TestHasActiveSubscription(TestCase):
    def test_false_when_no_subscription(self):
        user = UserFactory()

        self.assertFalse(has_active_subscription(user))

    def test_true_when_subscription_active(self):
        subscription = SubscriptionFactory(
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )

        self.assertTrue(has_active_subscription(subscription.user))

    def test_false_when_subscription_inactive(self):
        subscription = SubscriptionFactory(plan_id=1)

        self.assertFalse(has_active_subscription(subscription.user))

    def test_false_when_team_subscription_inactive(self):
        team = TeamFactory(subscription__plan_id=1)
        team.team_users.create(user=UserFactory())

        self.assertFalse(has_active_subscription(team.team_users.first().user))

    def test_true_when_team_subscription_active(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )
        team.team_users.create(user=UserFactory())

        self.assertTrue(has_active_subscription(team.team_users.first().user))
