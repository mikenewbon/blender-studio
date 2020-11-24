# import datetime as dt
from typing import Optional, Any

from django.contrib import admin

# from django.contrib.auth.models import User
from django.db.models import ForeignKey  # , Q
from django.forms.models import ModelChoiceField
from django.http.request import HttpRequest

# from django.utils import timezone

from common.mixins import AdminUserDefaultMixin, ViewOnSiteMixin
from films.admin.mixins import EditLinkMixin
from films.models import production_logs, Asset


class ProductionLogEntryAssetInline(admin.StackedInline):
    model = production_logs.ProductionLogEntryAsset
    show_change_link = True
    extra = 0
    autocomplete_fields = [
        'asset',
    ]

    # TODO(Natalia): uncomment the filter kwargs when we finish development
    def formfield_for_foreignkey(
        self, db_field: 'ForeignKey[Any, Any]', request: Optional[HttpRequest], **kwargs: Any
    ) -> Optional[ModelChoiceField]:
        """Show only published assets created in the last 7 days by the current user."""
        # TODO(Natalia): add filtering by film, show assets since the last log
        if db_field.name == 'asset' and request is not None:
            kwargs['queryset'] = Asset.objects.filter(
                # Q(static_asset__author=request.user)
                # | (Q(static_asset__author__isnull=True) & Q(static_asset__user=request.user)),
                is_published=True,
                # date_created__gte=timezone.now() - dt.timedelta(days=7),
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(production_logs.ProductionLogEntry)
class ProductionLogEntryAdmin(AdminUserDefaultMixin, admin.ModelAdmin):
    inlines = [ProductionLogEntryAssetInline]
    date_hierarchy = 'production_log__start_date'
    list_display = ['__str__', 'production_log']
    list_filter = [
        'production_log__film',
        'production_log',
        'production_log__start_date',
    ]
    search_fields = [
        'production_log__name',
    ]
    readonly_fields = ['date_created']
    autocomplete_fields = ['author']

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     """Limit users to film crew members."""
    #     if db_field.name == 'user':
    #         try:
    #             object_id = request.resolver_match.kwargs['object_id']
    #         except KeyError:
    #             return super().formfield_for_foreignkey(db_field, request, **kwargs)
    #         film = production_logs.ProductionLog.objects.get(pk=object_id).film
    #         kwargs['queryset'] = User.objects.filter(film_crew__film=film).distinct()
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProductionLogEntryInline(EditLinkMixin, admin.StackedInline):
    model = production_logs.ProductionLogEntry
    show_change_link = True
    extra = 0
    autocomplete_fields = [
        'author',
        'user',
    ]


@admin.register(production_logs.ProductionLog)
class ProductionLogAdmin(AdminUserDefaultMixin, ViewOnSiteMixin, admin.ModelAdmin):
    inlines = [ProductionLogEntryInline]
    date_hierarchy = 'start_date'
    list_display = ['__str__', 'name', 'start_date', 'view_link']
    list_filter = ['film', 'start_date']
    search_fields = [
        'name',
    ]
    readonly_fields = ['date_created']
    autocomplete_fields = ['author', 'film']
    fieldsets = (
        (None, {'fields': ['film', 'name', 'start_date', 'user']}),
        ('Summary', {'fields': ['thumbnail', 'youtube_link', 'author', 'summary']}),
    )
