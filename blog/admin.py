from django.contrib import admin
from django.forms import Textarea

from blog.models import Post
from common.mixins import ViewOnSiteMixin
import search.signals


@admin.register(Post)
class PostAdmin(ViewOnSiteMixin, admin.ModelAdmin):
    list_display = [
        '__str__',
        'film',
        'author',
        'is_published',
        'date_published',
        'view_link',
    ]
    list_filter = [
        'is_published',
        'film',
    ]

    def formfield_for_dbfield(self, db_field, **kwargs):
        """Override display of "excerpt" field.

        Make it appear smaller than the content text area.
        """
        if db_field.name == 'excerpt':
            kwargs['widget'] = Textarea(attrs={'rows': 2, 'cols': 40})
        return super().formfield_for_dbfield(db_field, **kwargs)

    fields = (
        'date_published',
        'title',
        'slug',
        'category',
        'author',
        'film',
        'excerpt',
        'content',
        'attachments',
        'header',
        'thumbnail',
        'is_published',
    )
    autocomplete_fields = ['author', 'attachments', 'film']
    search_fields = ['slug']
    prepopulated_fields = {
        'slug': ('title',),
    }

    actions = [search.signals.reindex]
