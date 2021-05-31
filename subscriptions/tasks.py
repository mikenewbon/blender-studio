"""Subscriptions tasks, such as sending of the emails."""
from typing import Dict, Optional, Tuple
import logging

from background_task import background
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template import loader
from django.urls import reverse
import django.core.mail

import looper.models
import looper.signals

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def absolute_url(
    view_name: str, args: Optional[tuple] = None, kwargs: Optional[dict] = None
) -> str:
    """Same as django.urls.reverse() but then as absolute URL.

    For simplicity this assumes HTTPS is used.
    """
    from urllib.parse import urljoin

    domain = get_current_site(None).domain
    relative_url = reverse(view_name, args=args, kwargs=kwargs)
    return urljoin(f'https://{domain}/', relative_url)


def is_noreply(email: str) -> bool:
    """Return True if the email address is a no-reply address."""
    return email.startswith('noreply@') or email.startswith('no-reply@')


def _get_extra_context() -> Dict[str, str]:
    domain = get_current_site(None).domain
    return {
        'site_url': f'https://{domain}/',
        'billing_url': absolute_url('user-settings-billing'),
    }


def _construct_subscription_mail(
    subscription: looper.models.Subscription,
) -> Tuple[str, str, str]:
    """Construct a mail about a subscription.

    :return: tuple (html, text, subject)
    """
    if subscription.status == 'active':
        verb = 'activated'
    else:
        verb = 'deactivated'

    context = {
        'user': subscription.user,
        'customer': subscription.user.customer,
        'subscription': subscription,
        'verb': verb,
        **_get_extra_context(),
    }

    subject: str = loader.render_to_string(
        f'subscriptions/emails/subscription_{verb}_subject.txt', context
    )
    context['subject'] = subject.strip()

    email_body_html = loader.render_to_string(
        f'subscriptions/emails/subscription_{verb}.html', context
    )
    email_body_txt = loader.render_to_string(
        f'subscriptions/emails/subscription_{verb}.txt', context
    )

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
    logger.debug('Sending subscription-bank-info notification to %s', email)

    order = subscription.latest_order()
    assert order, "Can't send a notificaton about bank transfer without an existing order"

    context = {
        'user': subscription.user,
        'customer': subscription.user.customer,
        'subscription': subscription,
        'order': order,
        **_get_extra_context(),
    }

    subject: str = loader.render_to_string(
        'subscriptions/emails/bank_transfer_required_subject.txt', context
    ).strip()
    context['subject'] = subject

    email_body_html = loader.render_to_string(
        'subscriptions/emails/bank_transfer_required.html', context
    )
    email_body_txt = loader.render_to_string(
        'subscriptions/emails/bank_transfer_required.txt', context
    )

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

    logger.debug('Sending subscription-changed notification to %s', email)

    email_body_html, email_body_txt, subject = _construct_subscription_mail(subscription)

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
    order = looper.models.Order.get(pk=order_id)
    transaction = looper.models.Transaction.get(pk=transaction_id)
    user = order.user
    customer = user.customer
    billing_email = customer.billing_email or user.email
    logger.debug('Sending %r notification to %s', order.status, billing_email)

    subscription = order.subscription.subscription

    pay_url = absolute_url('looper:checkout_existing_order', kwargs={'order_id': order.pk})
    receipt_url = absolute_url('settings_receipt', kwargs={'order_id': order.pk})

    context = {
        'customer': customer,
        'email': billing_email,
        'order': order,
        'subscription': subscription,
        'pay_url': pay_url,
        'receipt_url': receipt_url,
        'failure_message': transaction.failure_message,
        'payment_method': transaction.payment_method.recognisable_name,
        'maximum_collection_attemps': settings.LOOPER_CLOCK_MAX_AUTO_ATTEMPTS,
    }

    subject: str = loader.render_to_string(
        f'subscriptions/emails/payment_{order.status}_subject.txt', context
    ).strip()
    context['subject'] = subject

    email_body_html = loader.render_to_string(
        f'subscriptions/emails/payment_{order.status}.html', context
    )
    email_body_txt = loader.render_to_string(
        f'subscriptions/emails/payment_{order.status}.txt', context
    )

    django.core.mail.send_mail(
        subject,
        message=email_body_txt,
        html_message=email_body_html,
        from_email=None,  # just use the configured default From-address.
        recipient_list=[billing_email],
        fail_silently=False,
    )
    logger.info('Sent %r notification to %s', order.status, billing_email)


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
    subs_admin_url = absolute_url(
        'admin:looper_subscription_change',
        kwargs={'object_id': subscription.id},
    )

    context = {
        'user': user,
        'subscription': subscription,
        'subs_admin_url': subs_admin_url,
    }

    subject: str = loader.render_to_string(
        'subscriptions/emails/managed_notification_subject.txt', context
    ).strip()
    context['subject'] = subject

    email_body_html = loader.render_to_string(
        'subscriptions/emails/managed_notification.html', context
    )
    email_body_txt = loader.render_to_string(
        'subscriptions/emails/managed_notification.txt', context
    )

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
