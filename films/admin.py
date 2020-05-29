from django.contrib import admin

from films.models import collections, films

admin.site.register(collections.Collection)
admin.site.register(films.Film)
