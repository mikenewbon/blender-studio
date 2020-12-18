from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import get_user_model, admin as auth_admin

import profiles.models as profiles_models


class ProfileInlineAdmin(admin.StackedInline):
    model = profiles_models.Profile

    def has_delete_permission(self, request, obj=None):
        """Fake delete permission to hide the Delete checkbox."""
        return False


class _IsSubscribedToNewsletterFilter(SimpleListFilter):
    title = 'Is subscribed to newsletter'
    parameter_name = 'is_subscribed_to_newsletter'

    def lookups(self, request, model_admin):
        return (
            (None, 'All'),
            (1, 'Yes'),
            (0, 'No'),
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == (str(lookup) if lookup is not None else lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(profile__is_subscribed_to_newsletter=self.value())
        return queryset


@admin.register(get_user_model())
class UserAdmin(auth_admin.UserAdmin):
    inlines = [ProfileInlineAdmin]
    list_filter = auth_admin.UserAdmin.list_filter + (_IsSubscribedToNewsletterFilter,)
    list_display = ['full_name'] + [
        _ for _ in auth_admin.UserAdmin.list_display if _ not in ('first_name', 'last_name')
    ]

    def full_name(self, obj):
        """Return profile's full name."""
        return obj.profile.full_name if obj.profile else ''
