from django.contrib import admin

from films.models import assets, collections, films


class AssetCommentInline(admin.TabularInline):
    model = assets.AssetComment
    show_change_link = True
    extra = 0


@admin.register(assets.Asset)
class AssetAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AssetCommentInline]
    readonly_fields = ['date_created']
    list_display = ['__str__', 'order', 'film', 'collection']
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
    search_fields = [
        'name',
        'film__title',
        'collection__name',
        'static_asset__user__first_name',
        'static_asset__user__last_name',
        'static_asset__author__first_name',
        'static_asset__author__last_name',
    ]
    autocomplete_fields = ['static_asset']


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


@admin.register(films.Film)
class FilmAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
