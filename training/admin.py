from django.contrib import admin

from training.models import trainings, chapters, sections, tags


class ChapterInline(admin.TabularInline):
    show_change_link = True
    model = chapters.Chapter


class TagInline(admin.TabularInline):
    model = trainings.TrainingTag


@admin.register(trainings.Training)
class TrainingAdmin(admin.ModelAdmin):
    inlines = [ChapterInline, TagInline]


class SectionInline(admin.TabularInline):
    show_change_link = True
    model = sections.Section


@admin.register(chapters.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    inlines = [SectionInline]


class VideoInline(admin.TabularInline):
    show_change_link = True
    model = sections.Video


class AssetInline(admin.TabularInline):
    show_change_link = True
    model = sections.Asset


@admin.register(sections.Section)
class SectionAdmin(admin.ModelAdmin):
    inlines = [VideoInline, AssetInline]


admin.site.register(sections.Video)
admin.site.register(sections.Asset)
admin.site.register(tags.Tag)
