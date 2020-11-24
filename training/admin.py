from typing import Callable, TypeVar

from django.contrib import admin
from django.utils.html import format_html


from common import mixins
from training.models import chapters, sections, trainings, flatpages
import static_assets.models as models_static_assets

T = TypeVar('T', bound=Callable[..., object])


def with_name(name: str, func: T) -> T:
    func.__name__ = name
    return func


class ChapterInline(admin.TabularInline):
    show_change_link = True
    exclude = ['description', 'user']
    model = chapters.Chapter
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)
    autocomplete_fields = ['user']


# class TagInline(admin.TabularInline):
#     model = trainings.TrainingTag


@admin.register(trainings.Training)
class TrainingAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        '__str__',
        'is_published',
        'is_featured',
        with_name('url', lambda obj: format_html('<a href="{url}">{url}</a>', url=obj.url)),
    ]
    search_fields = [
        'name',
    ]
    inlines = [ChapterInline]


class SectionInline(admin.TabularInline):
    show_change_link = True
    model = sections.Section
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)
    autocomplete_fields = ['static_asset', 'user', 'attachments']


@admin.register(chapters.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['training', 'user']
    inlines = [SectionInline]
    search_fields = [
        'name',
    ]
    list_filter = [
        'training',
    ]
    list_display = ['__str__', 'is_published']
    list_editable = ['is_published']


class StaticAssetInline(admin.TabularInline):
    show_change_link = True
    model = models_static_assets.StaticAsset
    search_fields = ['name']


@admin.register(sections.Section)
class SectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        '__str__',
        with_name(
            'url', lambda obj: format_html('<a href="{url}" target="_blank">View</a>', url=obj.url)
        ),
        'is_published',
        'is_free',
        'is_featured',
    ]
    list_editable = ['is_published', 'is_free', 'is_featured']
    # inlines = [
    #     StaticAssetInline,
    # ]
    list_filter = [
        'chapter__training__type',
        'chapter__training__difficulty',
        'chapter__training',
        'is_published',
        'is_free',
        'is_featured',
    ]
    list_per_page = 20
    search_fields = ['name', 'chapter__name', 'chapter__training__name', 'slug']
    autocomplete_fields = ['chapter', 'static_asset', 'user', 'attachments']


@admin.register(flatpages.TrainingFlatPage)
class TrainingFlatPageAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    autocomplete_fields = ['training', 'attachments']
    list_display = ('title', 'training', 'view_link')
    list_filter = [
        'training',
    ]
    prepopulated_fields = {'slug': ('slug',)}
    raw_id_fields = ['training', 'attachments']
