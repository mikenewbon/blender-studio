from django.contrib.auth import get_user_model
from django.db import models

import looper.models

from common import mixins

User = get_user_model()


class Team(mixins.CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=256)
    users = models.ManyToManyField(User, through='TeamUsers', related_name='teams')
    subscription = models.OneToOneField(
        looper.models.Subscription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='team',
    )


class TeamUsers(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        verbose_name = 'Team Users'
        verbose_name_plural = 'Team Users'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_users')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_users')


class SubscriptionProperties(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        verbose_name = 'Subscription Properties'
        verbose_name_plural = 'Subscription Properties'

    plan = models.OneToOneField(
        looper.models.Subscription, on_delete=models.CASCADE, related_name='properties'
    )

    seats = models.IntegerField(blank=True, null=True)
