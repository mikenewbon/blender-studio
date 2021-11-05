from django.contrib import admin

from common.mixins import ViewOnSiteMixin
from characters.models import Character, CharacterVersion, CharacterShowcase


class CharacterVersionAdmin(admin.StackedInline):
    model = CharacterVersion
    autocomplete_fields = ['static_asset', 'preview_video_static_asset']
    extra = 0
    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('is_published', 'is_free', 'number', 'min_blender_version'),
                    'date_published',
                )
            },
        ),
        (
            None,
            {'fields': (('static_asset', 'preview_video_static_asset', 'preview_youtube_link'),)},
        ),
        (None, {'fields': (('description',),)}),
    )


class CharacterShowcaseAdmin(admin.StackedInline):
    model = CharacterShowcase
    autocomplete_fields = ['static_asset', 'preview_video_static_asset']
    extra = 0
    fieldsets = (
        (None, {'fields': (('is_published', 'is_free', 'min_blender_version'), 'date_published')}),
        (
            None,
            {'fields': (('static_asset', 'preview_video_static_asset', 'preview_youtube_link'),)},
        ),
        (None, {'fields': (('title', 'description'),)}),
    )


@admin.register(Character)
class CharacterAdmin(ViewOnSiteMixin, admin.ModelAdmin):
    save_on_top = True
    list_display = [
        '__str__',
        'film',
        'is_published',
        'date_published',
        'view_link',
    ]
    list_filter = [
        'is_published',
        'film',
    ]
    autocomplete_fields = ['film']
    prepopulated_fields = {
        'slug': ('name',),
    }
    inlines = [CharacterVersionAdmin, CharacterShowcaseAdmin]
