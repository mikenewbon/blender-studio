from typing import Callable, TypeVar

from django.contrib import admin
from django.utils.html import format_html

from training.models import chapters, sections, tags, trainings

T = TypeVar('T', bound=Callable[..., object])


def with_name(name: str, func: T) -> T:
    func.__name__ = name
    return func


class ChapterInline(admin.TabularInline):
    show_change_link = True
    model = chapters.Chapter
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)


class TagInline(admin.TabularInline):
    model = trainings.TrainingTag


@admin.register(trainings.Training)
class TrainingAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        '__str__',
        with_name('url', lambda obj: format_html('<a href="{url}">{url}</a>', url=obj.url)),
    ]
    inlines = [ChapterInline, TagInline]


class SectionInline(admin.TabularInline):
    show_change_link = True
    model = sections.Section
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)


@admin.register(chapters.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SectionInline]


class VideoInline(admin.TabularInline):
    show_change_link = True
    model = sections.Video


class AssetInline(admin.TabularInline):
    show_change_link = True
    model = sections.Asset


class SectionCommentInline(admin.TabularInline):
    show_change_link = True
    model = sections.SectionComment
    extra = 0


@admin.register(sections.Section)
class SectionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = [
        '__str__',
        with_name('url', lambda obj: format_html('<a href="{url}">{url}</a>', url=obj.url)),
    ]
    inlines = [VideoInline, AssetInline, SectionCommentInline]
    list_filter = [
        'chapter__training__type',
        'chapter__training__difficulty',
        'chapter__training',
        'chapter',
    ]
    search_fields = ['name', 'chapter__name', 'chapter__training__name']


admin.site.register(sections.Video)
admin.site.register(sections.Asset)
admin.site.register(tags.Tag)
