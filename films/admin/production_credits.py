from django.contrib import admin

from films.models import FilmProductionCredit


@admin.register(FilmProductionCredit)
class FilmProductionCreditAdmin(admin.ModelAdmin):
    autocomplete_fields = ['film', 'user']
    readonly_fields = ['date_created', 'date_updated']
    list_display = ('film', 'display_name', 'is_public')
    list_filter = [
        'film',
    ]
