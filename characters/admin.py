from django.contrib import admin

from common.mixins import ViewOnSiteMixin
from characters.models import Character, CharacterVersion, CharacterShowcase


class CharacterVersionAdmin(admin.TabularInline):
    model = CharacterVersion
    autocomplete_fields = ['static_asset']
    extra = 0


class CharacterShowcaseAdmin(admin.TabularInline):
    model = CharacterShowcase
    autocomplete_fields = ['static_asset']
    extra = 0


@admin.register(Character)
class PostAdmin(ViewOnSiteMixin, admin.ModelAdmin):
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
