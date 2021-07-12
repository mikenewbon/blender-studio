"""Subscriptions tasks, such as sending of the emails."""
from typing import Tuple, Dict, Any
import logging

from background_task import background
from django.conf import settings
from django.template import loader
import django.core.mail

import looper.models
import looper.signals

from common import mailgun
from emails.util import get_template_context, absolute_url, is_noreply

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _construct_subscription_mail(mail_name: str, context: Dict[str, Any]) -> Tuple[str, str, str]:
    """Construct a mail about a subscription.

    :return: tuple (html, text, subject)
    """
    base_path = 'subscriptions/emails'
    subj_tmpl, html_tmpl, txt_tmpl = (
        f'{base_path}/{mail_name}_subject.txt',
        f'{base_path}/{mail_name}.html',
        f'{base_path}/{mail_name}.txt',
    )

    subject: str = loader.render_to_string(subj_tmpl, context)
    context['subject'] = subject.strip()

    email_body_html = loader.render_to_string(html_tmpl, context)
    email_body_txt = loader.render_to_string(txt_tmpl, context)
    return email_body_html, email_body_txt, context['subject']


@background()
def send_mail_bank_transfer_required(subscription_id: int):
    """Send out an email notifying about the required bank transfer payment."""
    subscription = looper.models.Subscription.objects.get(pk=subscription_id)
    user = subscription.user
    email = user.customer.billing_email or user.email
    assert (
        email
    ), f'Cannot send notification about bank payment for subscription {subscription.pk}: no email'
    if is_noreply(email):
        logger.debug(
            'Not sending subscription-bank-info notification to no-reply address %s', email
        )
        return

    # An Unsubscribe record will prevent this message from being delivered by Mailgun.
    # This records might have been previously created for an existing account.
    mailgun.delete_unsubscribe_record(email)

    logger.debug('Sending subscription-bank-info notification to %s', email)

    order = subscription.latest_order()
    assert order, "Can't send a notificaton about bank transfer without an existing order"

    context = {
        'user': subscription.user,
        'subscription': subscription,
        'order': order,
        **get_template_context(),
    }

    mail_name = 'bank_transfer_required'
    email_body_html, email_body_txt, subject = _construct_subscription_mail(mail_name, context)

    django.core.mail.send_mail(
        subject,
        message=email_body_txt,
        html_message=email_body_html,
        from_email=None,  # just use the configured default From-address.
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info('Sent notification about bank transfer to %s', email)


@background()
def send_mail_subscription_status_changed(subscription_id: int):
    """Send out an email notifying about the activated subscription."""
    subscription = looper.models.Subscription.objects.get(pk=subscription_id)
    user = subscription.user
    email = user.customer.billing_email or user.email
    assert email, f'Cannot send notification about subscription {subscription.pk} status: no email'
    if is_noreply(email):
        raise
        logger.debug('Not sending subscription-changed notification to no-reply address %s', email)
        return

    # An Unsubscribe record will prevent this message from being delivered by Mailgun.
    # This records might have been previously created for an existing account.
    mailgun.delete_unsubscribe_record(email)

    logger.debug('Sending subscription-changed notification to %s', email)

    if subscription.status == 'active':
        verb = 'activated'
    else:
        verb = 'deactivated'

    context = {
        'user': subscription.user,
        'subscription': subscription,
        'verb': verb,
        **get_template_context(),
    }
    mail_name = f'subscription_{verb}'
    email_body_html, email_body_txt, subject = _construct_subscription_mail(mail_name, context)

    django.core.mail.send_mail(
        subject,
        message=email_body_txt,
        html_message=email_body_html,
        from_email=None,  # just use the configured default From-address.
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info('Sent subscription-changed notification to %s', email)


@background()
def send_mail_automatic_payment_performed(order_id: int, transaction_id: int):
    """Send out an email notifying about the soft-failed payment."""
    order = looper.models.Order.objects.get(pk=order_id)
    transaction = looper.models.Transaction.objects.get(pk=transaction_id)
    user = order.user
    customer = user.customer
    email = customer.billing_email or user.email
    logger.debug('Sending %r notification to %s', order.status, email)

    # An Unsubscribe record will prevent this message from being delivered by Mailgun.
    # This records might have been previously created for an existing account.
    mailgun.delete_unsubscribe_record(email)

    subscription = order.subscription

    pay_url = absolute_url('subscriptions:pay-existing-order', kwargs={'order_id': order.pk})
    receipt_url = absolute_url('subscriptions:receipt', kwargs={'order_id': order.pk})

    context = {
        'user': subscription.user,
        'email': email,
        'order': order,
        'subscription': subscription,
        'pay_url': pay_url,
        'receipt_url': receipt_url,
        'failure_message': transaction.failure_message,
        'payment_method': transaction.payment_method.recognisable_name,
        'maximum_collection_attemps': settings.LOOPER_CLOCK_MAX_AUTO_ATTEMPTS,
        **get_template_context(),
    }

    mail_name = f'payment_{order.status}'
    email_body_html, email_body_txt, subject = _construct_subscription_mail(mail_name, context)

    django.core.mail.send_mail(
        subject,
        message=email_body_txt,
        html_message=email_body_html,
        from_email=None,  # just use the configured default From-address.
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info('Sent %r notification to %s', order.status, email)


@background()
def send_mail_managed_subscription_notification(subscription_id: int):
    """Send out an email notifying a manager about an expiring managed subscription."""
    subscription = looper.models.Subscription.objects.get(pk=subscription_id)
    email = settings.LOOPER_MANAGER_MAIL
    logger.debug(
        'Notifying %s about managed subscription %r passing its next_payment date',
        email,
        subscription.pk,
    )

    user = subscription.user
    admin_url = absolute_url(
        'admin:looper_subscription_change',
        kwargs={'object_id': subscription.id},
    )

    context = {
        'user': user,
        'subscription': subscription,
        'admin_url': admin_url,
        **get_template_context(),
    }

    mail_name = 'managed_notification'
    email_body_html, email_body_txt, subject = _construct_subscription_mail(mail_name, context)

    django.core.mail.send_mail(
        subject,
        message=email_body_txt,
        html_message=email_body_html,
        from_email=None,  # just use the configured default From-address.
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info(
        'Notified %s about managed subscription %r passing its next_payment date',
        email,
        subscription.pk,
    )
