from typing import Callable, TypeVar

from django.contrib import admin
from django.utils.html import format_html

from training.models import chapters, sections, trainings
import static_assets.models as models_static_assets

T = TypeVar('T', bound=Callable[..., object])


def with_name(name: str, func: T) -> T:
    func.__name__ = name
    return func


class ChapterInline(admin.TabularInline):
    show_change_link = True
    model = chapters.Chapter
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)


# class TagInline(admin.TabularInline):
#     model = trainings.TrainingTag


@admin.register(trainings.Training)
class TrainingAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        '__str__',
        with_name('url', lambda obj: format_html('<a href="{url}">{url}</a>', url=obj.url)),
    ]
    inlines = [ChapterInline]


class SectionInline(admin.TabularInline):
    show_change_link = True
    model = sections.Section
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)
    autocomplete_fields = ['static_asset']


@admin.register(chapters.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SectionInline]
    search_fields = ['name']


class StaticAssetInline(admin.TabularInline):
    show_change_link = True
    model = models_static_assets.StaticAsset


@admin.register(sections.Section)
class SectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        '__str__',
        with_name(
            'url', lambda obj: format_html('<a href="{url}" target="_blank">View</a>', url=obj.url)
        ),
    ]
    # inlines = [
    #     StaticAssetInline,
    # ]
    list_filter = [
        'chapter__training__type',
        'chapter__training__difficulty',
        'chapter__training',
    ]
    list_per_page = 20
    search_fields = ['name', 'chapter__name', 'chapter__training__name']
    autocomplete_fields = ['chapter', 'static_asset']
