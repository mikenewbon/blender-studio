from typing import Optional, Any

from django.contrib import admin
from django.db.models import ForeignKey, Q
from django.forms.models import ModelChoiceField
from django.http.request import HttpRequest

from films.admin.mixins import EditLinkMixin
from films.models import production_logs, Asset


class ProductionLogEntryAssetInline(admin.StackedInline):
    model = production_logs.ProductionLogEntryAsset
    show_change_link = True
    extra = 0

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: Optional[HttpRequest], **kwargs: Any
    ) -> Optional[ModelChoiceField]:
        if db_field.name == 'asset':
            kwargs['queryset'] = Asset.objects.filter(
                Q(static_asset__author=request.user)
                | (Q(static_asset__author__isnull=True) & Q(static_asset__user=request.user))
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(production_logs.ProductionLogEntry)
class ProductionLogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'production_log__start_date'
    list_display = ['__str__', 'production_log']
    inlines = [ProductionLogEntryAssetInline]
    list_filter = ['production_log__film', 'production_log', 'user', 'author']


class ProductionLogEntryInline(EditLinkMixin, admin.StackedInline):
    model = production_logs.ProductionLogEntry
    show_change_link = True
    extra = 0


@admin.register(production_logs.ProductionLog)
class ProductionLogAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'name']
    inlines = [ProductionLogEntryInline]
