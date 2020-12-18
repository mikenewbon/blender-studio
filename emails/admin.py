from django.conf import settings
from django.contrib import admin, messages
from django.template import Template, Context
from django.utils.safestring import mark_safe
import anymail.exceptions

from emails.models import Email

iframe_template = Template(
    '<iframe sandbox style="width: 100%; height: 100vh;" srcdoc="{{ body|safe }}"></iframe>'
)


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    class Media:
        css = {'all': (f'{settings.STATIC_URL}/emails/admin/email.css',)}

    def rendered_html(self, obj) -> str:
        """Preview the HTML version of the email."""
        # Escape " and & to avoid breaking srcdoc. Order of escaping is important.
        body = obj.render_html().replace('&', '&amp;').replace('"', '&quot;')
        context = Context({'body': body})
        rendered: str = iframe_template.render(context)
        return mark_safe(rendered)

    rendered_html.allow_tags = True
    rendered_html.short_description = "Preview"

    list_display = ['subject', 'from_email', 'to']
    readonly_fields = ['rendered_html', 'date_sent']
    actions = ['send']

    def send(self, request, queryset):
        """Custom action for sending an email."""
        for email in queryset:
            try:
                email.send()
                msg = f'Message "{email.subject}" sent to {email.to}'
                self.message_user(request, msg, messages.SUCCESS)
            except anymail.exceptions.AnymailRequestsAPIError as e:
                self.message_user(request, str(e), messages.ERROR)

    send.short_description = "Send selected emails"
