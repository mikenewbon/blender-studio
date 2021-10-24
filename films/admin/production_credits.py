import csv

from django.contrib import admin, messages
from django.http import HttpResponse

from films.models import FilmProductionCredit


@admin.register(FilmProductionCredit)
class FilmProductionCreditAdmin(admin.ModelAdmin):
    autocomplete_fields = ['film', 'user']
    readonly_fields = ['date_created', 'date_updated']
    list_display = (
        'film',
        'full_name',
        'display_name',
        'is_public',
    )
    list_filter = ['film', 'is_public']
    search_fields = ['user__email', 'user__full_name', 'user__username']
    actions = ['generate_mailing_list_from_selected', 'make_read_only']

    def generate_mailing_list_from_selected(self, request, queryset):
        """Custom action for generating a CSV of emails for a mailing list."""
        filename = 'production_credits_maillist.csv'
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        writer = csv.writer(response)
        for credit in queryset:
            values = []
            if credit.user.full_name:
                values.append(credit.user.full_name)
            values.append(credit.user.email)
            writer.writerow(values)
        return response

    generate_mailing_list_from_selected.short_description = (
        "Generate a mailing list from selected (CSV)"
    )

    def make_read_only(self, request, queryset):
        for credit in queryset:
            if credit.is_public:
                credit.display_name = credit.user.full_name
            credit.is_editable = False
            credit.save()
        self.message_user(
            request,
            '%d credits was successfully marked as read-only.' % len(queryset),
            messages.SUCCESS,
        )

    make_read_only.short_description = "Mark selected credit(s) as read-only"

    def full_name(self, obj) -> str:  # noqa: D102
        return f"{obj.user.full_name or '--'}"
