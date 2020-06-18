from django.contrib import admin

from films.models import collections, films, assets, production_logs


class ProductionLogEntryAssetInline(admin.TabularInline):
    show_change_link = True
    model = production_logs.ProductionLogEntryAsset


@admin.register(production_logs.ProductionLogEntry)
class ProductionLogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'production_log__start_date'
    list_display = ['__str__', 'production_log']
    inlines = [ProductionLogEntryAssetInline]


@admin.register(production_logs.ProductionLog)
class ProductionLogAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'name']


admin.site.register(assets.Asset)
admin.site.register(collections.Collection)
admin.site.register(films.Film)
