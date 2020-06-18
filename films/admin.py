from typing import Optional, Sequence, Union, Callable

from django.contrib import admin
from django.db.models import Model
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.safestring import mark_safe

from films.models import collections, films, assets, production_logs


class ProductionLogEntryAssetInline(admin.StackedInline):
    model = production_logs.ProductionLogEntryAsset
    show_change_link = True
    extra = 1


@admin.register(production_logs.ProductionLogEntry)
class ProductionLogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'production_log__start_date'
    list_display = ['__str__', 'production_log']
    inlines = [ProductionLogEntryAssetInline]


class ProductionLogEntryInline(admin.StackedInline):
    model = production_logs.ProductionLogEntry
    show_change_link = True
    extra = 1
    readonly_fields = ['get_edit_link']

    def get_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Sequence[Union[Callable, str]]:
        fields = ['get_edit_link', *super().get_fields(request, obj)]
        return fields

    def get_edit_link(self, obj: Optional[production_logs.ProductionLogEntry] = None) -> str:
        if obj.pk:
            url = reverse(
                f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk]
            )
            return mark_safe(f'<a href="{url}">Edit this {obj._meta.verbose_name} separately</a>')
        return 'Save and continue editing to create a link'

    get_edit_link.short_description = 'Edit link'


@admin.register(production_logs.ProductionLog)
class ProductionLogAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'name']
    inlines = [ProductionLogEntryInline]


admin.site.register(assets.Asset)
admin.site.register(collections.Collection)
admin.site.register(films.Film)
