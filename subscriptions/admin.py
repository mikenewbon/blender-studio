from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
import django.forms

import looper.admin
import looper.admin.mixins

from subscriptions import models

User = get_user_model()
manager_link = looper.admin.create_admin_fk_link(
    'manager', 'manager', looper.admin._get_admin_url_name(User)
)
team_member_link = looper.admin.create_admin_fk_link(
    'user', 'view in admin', looper.admin._get_admin_url_name(User)
)

# Blender Studio subscriptions override Plan and Subscription, adding team properties
admin.site.unregister(looper.models.Plan)
admin.site.unregister(looper.models.Subscription)


class TeamPlanPropertiesInlineAdmin(admin.TabularInline):
    model = models.TeamPlanProperties
    extra = 0


class TeamInlineAdmin(admin.TabularInline):
    model = models.Team
    formfield_overrides = {ArrayField: {'widget': django.forms.Textarea}}
    extra = 0


@admin.register(looper.models.Plan)
class PlanAdmin(looper.admin.PlanAdmin):
    inlines = looper.admin.PlanAdmin.inlines + [TeamPlanPropertiesInlineAdmin]


@admin.register(looper.models.Subscription)
class SubscriptionAdmin(looper.admin.SubscriptionAdmin):
    inlines = [TeamInlineAdmin] + looper.admin.SubscriptionAdmin.inlines


class TeamUserInlineAdmin(
    looper.admin.mixins.NoAddDeleteMixin, looper.admin.mixins.NoChangeMixin, admin.TabularInline
):
    model = models.TeamUsers
    verbose_name = 'team member'
    verbose_name_plural = 'team members'
    readonly_fields = [team_member_link]
    extra = 0
