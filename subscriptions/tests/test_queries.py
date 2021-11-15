from django.test import TestCase

from common.tests.factories.users import UserFactory
from common.tests.factories.subscriptions import SubscriptionFactory, TeamFactory

import looper.models

from subscriptions.queries import (
    has_active_subscription,
    has_subscription,
    has_non_legacy_subscription,
    has_not_yet_cancelled_subscription,
)


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


class TestHasNotYetCancelledSubscription(TestCase):
    def test_false_when_no_subscription(self):
        user = UserFactory()

        self.assertFalse(has_not_yet_cancelled_subscription(user))

    def test_true_when_subscription_active(self):
        subscription = SubscriptionFactory(
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )

        self.assertTrue(has_not_yet_cancelled_subscription(subscription.user))

    def test_false_when_subscription_cancelled(self):
        subscription = SubscriptionFactory(plan_id=1, status='cancelled')

        self.assertFalse(has_not_yet_cancelled_subscription(subscription.user))

    def test_true_when_subscription_inactive(self):
        subscription = SubscriptionFactory(plan_id=1)

        self.assertTrue(has_not_yet_cancelled_subscription(subscription.user))

    def test_false_when_team_subscription_inactive(self):
        team = TeamFactory(subscription__plan_id=1)
        team.team_users.create(user=UserFactory())

        self.assertFalse(has_not_yet_cancelled_subscription(team.team_users.first().user))

    def test_false_when_team_subscription_active(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )
        team.team_users.create(user=UserFactory())

        self.assertFalse(has_not_yet_cancelled_subscription(team.team_users.first().user))

    def test_false_when_team_subscription_cancelled(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status='cancelled',
        )
        team.team_users.create(user=UserFactory())

        self.assertFalse(has_not_yet_cancelled_subscription(team.team_users.first().user))

    def test_true_when_team_subscription_cancelled_personal_active(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status='cancelled',
        )
        team.team_users.create(user=UserFactory())
        SubscriptionFactory(
            user=team.team_users.first().user,
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )

        self.assertTrue(has_not_yet_cancelled_subscription(team.team_users.first().user))

    def test_false_when_team_subscription_active_personal_cancelled(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )
        team.team_users.create(user=UserFactory())
        SubscriptionFactory(
            user=team.team_users.first().user,
            plan_id=1,
            status='cancelled',
        )

        self.assertFalse(has_not_yet_cancelled_subscription(team.team_users.first().user))


class TestHasSubscription(TestCase):
    def test_false_when_no_subscription(self):
        user = UserFactory()

        self.assertFalse(has_subscription(user))

    def test_true_when_subscription_active(self):
        subscription = SubscriptionFactory(
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )

        self.assertTrue(has_subscription(subscription.user))

    def test_true_when_subscription_inactive(self):
        subscription = SubscriptionFactory(plan_id=1)

        self.assertTrue(has_subscription(subscription.user))

    def test_true_when_team_subscription_inactive(self):
        team = TeamFactory(subscription__plan_id=1)
        team.team_users.create(user=UserFactory())

        self.assertTrue(has_subscription(team.team_users.first().user))

    def test_true_when_team_subscription_active(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )
        team.team_users.create(user=UserFactory())

        self.assertTrue(has_subscription(team.team_users.first().user))

    def test_true_when_subscription_active_is_legacy(self):
        subscription = SubscriptionFactory(
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
            is_legacy=True,
        )

        self.assertTrue(has_subscription(subscription.user))

    def test_true_when_subscription_inactive_and_is_legacy(self):
        subscription = SubscriptionFactory(plan_id=1, is_legacy=True)

        self.assertTrue(has_subscription(subscription.user))

    def test_true_when_team_subscription_inactive_and_is_legacy(self):
        team = TeamFactory(subscription__plan_id=1, subscription__is_legacy=True)
        team.team_users.create(user=UserFactory())

        self.assertTrue(has_subscription(team.team_users.first().user))


class TestHasNonLegacySubscription(TestCase):
    def test_false_when_no_subscription(self):
        user = UserFactory()

        self.assertFalse(has_non_legacy_subscription(user))

    def test_true_when_subscription_active_and_not_is_legacy(self):
        subscription = SubscriptionFactory(
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
        )

        self.assertTrue(has_non_legacy_subscription(subscription.user))

    def test_true_when_subscription_inactive_and_not_is_legacy(self):
        subscription = SubscriptionFactory(plan_id=1)

        self.assertTrue(has_non_legacy_subscription(subscription.user))

    def test_true_when_team_subscription_inactive_and_not_is_legacy(self):
        team = TeamFactory(subscription__plan_id=1)
        team.team_users.create(user=UserFactory())

        self.assertTrue(has_non_legacy_subscription(team.team_users.first().user))

    def test_false_when_subscription_inactive_and_is_legacy(self):
        subscription = SubscriptionFactory(plan_id=1, is_legacy=True)

        self.assertFalse(has_non_legacy_subscription(subscription.user))

    def test_false_when_subscription_active_and_is_legacy(self):
        subscription = SubscriptionFactory(
            plan_id=1,
            status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
            is_legacy=True,
        )

        self.assertFalse(has_non_legacy_subscription(subscription.user))

    def test_false_when_team_subscription_inactive_and_is_legacy(self):
        team = TeamFactory(subscription__plan_id=1, subscription__is_legacy=True)
        team.team_users.create(user=UserFactory())

        self.assertFalse(has_non_legacy_subscription(team.team_users.first().user))

    def test_false_when_team_subscription_active_and_is_legacy(self):
        team = TeamFactory(
            subscription__plan_id=1,
            subscription__status=list(looper.models.Subscription._ACTIVE_STATUSES)[0],
            subscription__is_legacy=True,
        )
        team.team_users.create(user=UserFactory())

        self.assertFalse(has_non_legacy_subscription(team.team_users.first().user))
