from django.contrib import admin

from films.admin.mixins import EditLinkMixin
from films.models import assets, collections, films


class AssetInline(admin.StackedInline):
    model = assets.Asset
    extra = 1


@admin.register(collections.Collection)
class CollectionAdmin(admin.ModelAdmin):
    inlines = [AssetInline]


class CollectionInline(EditLinkMixin, admin.StackedInline):
    model = collections.Collection
    extra = 1


@admin.register(films.Film)
class FilmAdmin(admin.ModelAdmin):
    inlines = [CollectionInline]
