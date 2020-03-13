import looper.models
from django.contrib.auth.models import User
from django.db import models

from common import mixins


class Subscriber(mixins.CreatedUpdatedMixin, models.Model):
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
