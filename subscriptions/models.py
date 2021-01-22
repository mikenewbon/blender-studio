from django.contrib.auth import get_user_model
from django.db import models

import looper.models

from common import mixins

User = get_user_model()


class Subscriber(mixins.CreatedUpdatedMixin, models.Model):
    # TODO(anna): set to SET_NULL to make sure all looper data remains intact when user is deleted
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscriber')
    customer = models.OneToOneField(
        looper.models.Customer, on_delete=models.CASCADE, related_name='subscriber'
    )


class Organization(mixins.CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=256)
    users = models.ManyToManyField(User, through='OrganizationUsers', related_name='organizations')
    customer = models.OneToOneField(
        looper.models.Customer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='organization',
    )


class OrganizationUsers(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        verbose_name = 'Organization Users'
        verbose_name_plural = 'Organization Users'

    # TODO(anna): set to SET_NULL to make sure all looper data remains intact when user is deleted
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_users')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='organization_users'
    )

    can_change_organization = models.BooleanField(default=False)


class SubscriptionProperties(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        verbose_name = 'Subscription Properties'
        verbose_name_plural = 'Subscription Properties'

    plan = models.OneToOneField(
        looper.models.Subscription, on_delete=models.CASCADE, related_name='properties'
    )

    seats = models.IntegerField(blank=True, null=True)
