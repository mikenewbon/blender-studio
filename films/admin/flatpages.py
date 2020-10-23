from django.contrib import admin

from films.models import flatpages
from common import mixins


@admin.register(flatpages.FilmFlatPage)
class FilmFlatPageAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    autocomplete_fields = ['film', 'attachments']
    list_display = ('title', 'film', 'view_link')
    list_filter = [
        'film',
    ]
    prepopulated_fields = {'slug': ('slug',)}
