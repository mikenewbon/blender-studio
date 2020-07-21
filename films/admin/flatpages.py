from django.contrib import admin

from films.models import flatpages

admin.site.register(flatpages.FilmFlatPage)
