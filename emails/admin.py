from datetime import timedelta
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.template import Template, Context
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import anymail.exceptions
import django.core.mail

import looper.admin.mixins
import looper.models
import looper.taxes

from blog.models import Post
from common.queries import get_latest_trainings_and_production_lessons
from emails.models import Email
from emails.util import get_template_context
from subscriptions.tasks import _construct_subscription_mail

logger = logging.getLogger(__name__)
User = get_user_model()
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

    def was_sent(self, obj):
        """Display yes/no icon sent status."""
        return obj.date_sent is not None

    was_sent.boolean = True

    list_display = ['subject', 'from_email', 'to', 'was_sent']
    list_filter = ['reply_to', 'base_html_template', 'date_sent']
    readonly_fields = ['rendered_html', 'date_sent']
    actions = ['send']
    search_fields = ['to', 'subject']

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


class SubscriptionEmailPreview(Email):
    class Meta:
        proxy = True
        managed = False

    def render_html(self):
        """These emails already have their HTML rendered."""
        return self.html_message


@admin.register(SubscriptionEmailPreview)
class SubscriptionEmailPreviewAdmin(looper.admin.mixins.NoAddDeleteMixin, EmailAdmin):
    save_as_continue = True
    save_on_top = True

    list_display = ['subject', 'from_email']
    actions = []

    def _get_email_sent_message(self, obj):
        return f'Sent a test email "{obj.subject}" to {obj.to} from {obj.from_email}'

    def get_object(self, request, object_id, from_field=None):
        """Construct the Email on th fly from known subscription email templates."""
        user = User()
        user.customer = looper.models.Customer(full_name='Jane Doe')
        now = timezone.now()
        subscription = looper.models.Subscription(
            id=1234567890,
            user=user,
            payment_method=looper.models.PaymentMethod(
                method_type='cc',
                gateway_id=1,
                recognisable_name='Fake Credit Card payment method',
            ),
            price=1000,
            tax=160,
            tax_type=looper.taxes.TaxType.VAT_CHARGE.value,
            tax_rate=Decimal(19),
            next_payment=now + timedelta(days=10),
        )
        order = looper.models.Order(subscription=subscription)
        context = {
            'user': subscription.user,
            'subscription': subscription,
            'order': order,
            # Also add context for the expired email
            'latest_trainings': get_latest_trainings_and_production_lessons(),
            'latest_posts': Post.objects.filter(is_published=True)[:5],
            **get_template_context(),
        }
        mail_name = object_id
        email_body_html, email_body_txt, subject = _construct_subscription_mail(mail_name, context)
        return SubscriptionEmailPreview(
            id=mail_name,
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            reply_to=settings.DEFAULT_FROM_EMAIL,
            html_message=email_body_html,
            message=email_body_txt,
        )

    def _get_emails_list(self, request):
        emails = []
        for mail_name in (
            'bank_transfer_required',
            'subscription_activated',
            'subscription_deactivated',
            'payment_soft-failed',
            'payment_paid',
            'payment_failed',
            'managed_notification',
            'subscription_expired',
            'paypal_subscription_cancelled',
        ):
            emails.append(self.get_object(request, object_id=mail_name))
        return emails

    def _changeform_view(self, request, object_id, form_url, extra_context):
        """Change title of the change view to make it clear it's not actually changing anything."""
        template_name = object_id.replace('_5F', '_')
        extra_context = {
            **(extra_context or {}),
            'title': format_html(
                f'Previewing email rendered from the "<b>{template_name}</b>" template.'
                '<br/>You can adjust the content of the email before sending it, '
                'but these changes will not be persisted.'
            ),
        }
        return super()._changeform_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        """Send an email instead, display a notification about it."""
        django.core.mail.send_mail(
            obj.subject,
            message=obj.message,
            html_message=obj.html_message,
            from_email=obj.from_email,  # just use the configured default From-address.
            recipient_list=[obj.to],
            fail_silently=False,
        )

    def construct_change_message(self, request, form, formsets, add=False):
        """Log the fact that an email was sent."""
        obj = form.instance
        return self._get_email_sent_message(obj)

    def response_change(self, request, obj):
        """Override notification messages on change. Notify about successfully sent test email."""
        response = super().response_change(request, obj)
        # Clear the usual change messages: nothing was actually changed/saved, so they are confusing
        list(messages.get_messages(request))

        message = self._get_email_sent_message(obj)
        self.message_user(request, message, messages.INFO)
        return response

    def get_changelist_instance(self, request):
        """Monkey-patch changelist replacing the queryset with the existing transactional emails."""
        try:
            cl = super().get_changelist_instance(request)
            emails = self._get_emails_list(request)
            cl.result_list = emails
            cl.result_count = len(emails)
            cl.can_show_all = True
            cl.multi_page = False
            cl.title = 'Select an email to preview it'
            return cl
        except Exception as e:
            logger.exception(e)
            raise
