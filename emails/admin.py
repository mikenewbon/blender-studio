from django.contrib import admin, messages
from django.template import Template, Context
from django.utils.safestring import mark_safe
import anymail.exceptions

from emails.models import Email

iframe_template = Template('<iframe style="width: 100%" srcdoc="{{ body }}"></iframe>')


def send(modeladmin, request, queryset):
    for email in queryset:
        try:
            email.send()
        except anymail.exceptions.AnymailRequestsAPIError as e:
            messages.error(request, str(e))


send.short_description = "Send selected emails"


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    def rendered_html(self, obj) -> str:
        """Preview the HTML version of the email."""
        context = Context({'body': obj.render_html()})
        rendered: str = iframe_template.render(context)
        return mark_safe(rendered)

    rendered_html.allow_tags = True
    rendered_html.short_description = "Preview"

    list_display = ['subject', 'from_email', 'to']
    readonly_fields = ['rendered_html', 'date_sent']
    actions = [send]
