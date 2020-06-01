from django.contrib import admin

from films.models import collections, films, assets

admin.site.register(assets.Asset)
admin.site.register(collections.Collection)
admin.site.register(films.Film)
