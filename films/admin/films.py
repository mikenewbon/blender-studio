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
    autocomplete_fields = ['static_asset', 'attachments']

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[assets.Asset]':
        return super().get_queryset(request).select_related('film', 'collection__film')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit collections to the current film."""
        if db_field.name == 'collection':
            try:
                object_id = request.resolver_match.kwargs['object_id']
            except KeyError:
                return super().formfield_for_foreignkey(db_field, request, **kwargs)
            film = assets.Asset.objects.get(pk=object_id).film
            kwargs['queryset'] = collections.Collection.objects.filter(film=film).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class AssetInline(admin.StackedInline):
    model = assets.Asset
    show_change_link = True
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['date_created']
    extra = 0
    autocomplete_fields = ['static_asset', 'attachments', 'film']
    fields = ['static_asset', 'order', 'name', 'description', 'category', 'slug']


@admin.register(collections.Collection)
class CollectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AssetInline]
    list_display = ['__str__', 'film', 'order', 'parent']
    list_filter = ['film']
    search_fields = ['name', 'film__title']
    autocomplete_fields = ['parent', 'user', 'film']


class FilmCrewInlineAdmin(admin.TabularInline):
    model = films.Film.crew.through
    verbose_name_plural = 'Crew'
    autocomplete_fields = ['user']


@admin.register(films.Film)
class FilmAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('title', 'view_link')
    prepopulated_fields = {'slug': ('title',)}
    inlines = (FilmCrewInlineAdmin,)
