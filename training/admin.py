from typing import Callable, TypeVar

from django.contrib import admin
from django.utils.html import format_html

import looper.admin
import looper.admin.mixins as looper_mixins

from common import mixins
from training.models import chapters, sections, trainings, flatpages, progress
import search.signals
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
    save_on_top = True
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

    actions = [search.signals.reindex]


class SectionInline(admin.TabularInline):
    show_change_link = True
    model = sections.Section
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('index',)
    autocomplete_fields = ['static_asset', 'user', 'attachments']


@admin.register(chapters.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    save_on_top = True
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
        'static_asset__source_type',
        'chapter__training__difficulty',
        'chapter__training',
        'is_published',
        'is_free',
        'is_featured',
    ]
    list_per_page = 20
    search_fields = [
        'name',
        'chapter__name',
        'chapter__training__name',
        'slug',
        'static_asset__source',
    ]
    autocomplete_fields = ['chapter', 'static_asset', 'user', 'attachments']

    actions = [search.signals.reindex]


@admin.register(flatpages.TrainingFlatPage)
class TrainingFlatPageAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    autocomplete_fields = ['training', 'attachments']
    list_display = ('title', 'training', 'view_link')
    list_filter = [
        'training',
    ]
    prepopulated_fields = {'slug': ('slug',)}
    raw_id_fields = ['training', 'attachments']


@admin.register(progress.UserSectionProgress)
class UserSectionProgressAdmin(looper_mixins.NoChangeMixin, admin.ModelAdmin):
    def has_add_permission(self, *args, **kwargs):
        """Never added via the admin."""
        return False

    model = progress.UserSectionProgress
    list_display = (
        looper.admin.user_link,
        'date_created',
        'date_updated',
        'section',
        'started_duration_pageview_duration',
        'finished_duration_pageview_duration',
        'started',
        'finished',
    )
    list_filter = ('started', 'finished', 'section__chapter__training')
