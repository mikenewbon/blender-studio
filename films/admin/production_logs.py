from django.contrib import admin

from films.admin.mixins import EditLinkMixin
from films.models import production_logs


class ProductionLogEntryAssetInline(admin.StackedInline):
    model = production_logs.ProductionLogEntryAsset
    show_change_link = True
    extra = 1


@admin.register(production_logs.ProductionLogEntry)
class ProductionLogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'production_log__start_date'
    list_display = ['__str__', 'production_log']
    inlines = [ProductionLogEntryAssetInline]


class ProductionLogEntryInline(EditLinkMixin, admin.StackedInline):
    model = production_logs.ProductionLogEntry
    show_change_link = True
    extra = 1


@admin.register(production_logs.ProductionLog)
class ProductionLogAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'name']
    inlines = [ProductionLogEntryInline]
