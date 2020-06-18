# mypy: ignore-errors
from typing import Optional, Sequence, Union, Callable, Any, List, Tuple

from django.contrib import admin
from django.db.models import Model
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.safestring import mark_safe

from films.models import collections, films, assets, production_logs


class EditLinkMixin:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert issubclass(
            cls, admin.options.InlineModelAdmin
        ), f'{cls.__name__} has to be a subclass of InlineModelAdmin to use the EditLinkMixin'

    def get_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Sequence[Union[Callable[..., Any], str]]:
        """Show the edit link at the top of the inline form"""
        fields = ['get_edit_link', *super().get_fields(request, obj)]
        return fields

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Union[List[str], Tuple[str]]:
        """Display (non-editable) Edit Link field in the form"""
        readonly_fields = ['get_edit_link', *super().get_readonly_fields(request, obj)]
        return readonly_fields

    def get_edit_link(self, obj: Model) -> str:
        """Create a link in the inline to a separate form for the nested object"""
        if obj.pk:
            url = reverse(
                f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk]
            )
            return mark_safe(f'<a href="{url}">Edit this {obj._meta.verbose_name} separately</a>')
        return 'Save and continue editing to create a link'

    get_edit_link.short_description = 'Edit link'


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


admin.site.register(assets.Asset)
