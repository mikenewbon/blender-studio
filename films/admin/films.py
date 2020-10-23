from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from films.models import assets, collections, films
from common import mixins


@admin.register(assets.Asset)
class AssetAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['date_created']
    list_display = ['__str__', 'order', 'film', 'collection']
    list_filter = [
        'film',
        'category',
        'is_published',
        'is_featured',
        'static_asset__source_type',
    ]
    search_fields = [
        'name',
        'film__title',
        'collection__name',
    ]
    autocomplete_fields = ['static_asset', 'collection']

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[assets.Asset]':
        return super().get_queryset(request).select_related('film', 'collection__film')


class AssetInline(admin.StackedInline):
    model = assets.Asset
    show_change_link = True
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['date_created']
    extra = 0
    autocomplete_fields = ['static_asset']


@admin.register(collections.Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AssetInline]
    list_display = ['__str__', 'film', 'order', 'parent']
    list_filter = ['film', 'parent']
    search_fields = ['name', 'film__title']
    autocomplete_fields = ['parent']


class FilmCrewInlineAdmin(admin.TabularInline):
    model = films.Film.crew.through
    verbose_name_plural = 'Crew'
    autocomplete_fields = ['user']


@admin.register(films.Film)
class FilmAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    search_fields = ['name']
    list_display = ('title', 'view_link')
    prepopulated_fields = {'slug': ('title',)}
    inlines = (FilmCrewInlineAdmin,)
