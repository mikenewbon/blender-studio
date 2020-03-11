from django.contrib.auth.models import User
from django.db import models
from looper.models import Plan, Subscription

from common import mixins


class MembershipLevel(mixins.CreatedUpdatedMixin, models.Model):
    plan = models.OneToOneField(Plan, on_delete=models.PROTECT)


class Membership(mixins.CreatedUpdatedMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    subscription = models.OneToOneField(Subscription, on_delete=models.PROTECT)
    level = models.ForeignKey(MembershipLevel, on_delete=models.PROTECT)
