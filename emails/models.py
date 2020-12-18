from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from common import mixins


class Email(mixins.CreatedUpdatedMixin, models.Model):
    subject = models.CharField(max_length=255, null=False, blank=False)
    from_email = models.CharField(max_length=255, null=False, blank=False)
    reply_to = models.CharField(
        null=False,
        blank=False,
        max_length=255,
        help_text="A single valid email address or a comma-separated list of valid email addresses",
    )
    to = models.CharField(
        null=False,
        blank=False,
        max_length=255,
        help_text="A single valid email address or a comma-separated list of valid email addresses",
    )
    message = models.TextField(help_text="Plain text body of the email", null=False, blank=False)
    html_message = models.TextField(help_text="HTML version of the email", null=False, blank=False)

    date_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Email {self.subject} from {self.from_email}'

    def render_html(self):
        return render_to_string('emails/email.html', {'email': self})

    def send(self):
        """Send this email."""
        recipient_list = [addr.strip() for addr in self.to.split(',')]
        reply_to = [addr.strip() for addr in self.reply_to.split(',')]
        msg = EmailMultiAlternatives(
            self.subject, self.message, self.from_email, recipient_list, reply_to=reply_to
        )
        msg.attach_alternative(self.render_html(), 'text/html')
        msg.send()
        self.date_sent = timezone.now()
        self.save(update_fields=['date_sent'])