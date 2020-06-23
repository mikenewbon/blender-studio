from django.contrib import admin

from films.admin.mixins import EditLinkMixin
from films.models import assets, collections, films


@admin.register(assets.Asset)
class AssetAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_filter = [
        'film',
        'collection',
        'category',
        'is_published',
        'is_featured',
        'static_asset__source_type',
        'static_asset__user',
        'static_asset__author',
    ]


class AssetInline(admin.StackedInline):
    model = assets.Asset
    show_change_link = True
    prepopulated_fields = {'slug': ('name',)}
    extra = 0


@admin.register(collections.Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AssetInline]
    list_display = ['__str__', 'film']
    list_filter = ['film', 'parent']


class CollectionInline(admin.StackedInline):
    model = collections.Collection
    show_change_link = True
    prepopulated_fields = {'slug': ('name',)}
    extra = 0
    list_filter = ['film', 'parent']


@admin.register(films.Film)
class FilmAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    # inlines = [CollectionInline]
    # TODO(Natalia): only show a link or paginate collections in Change form?
