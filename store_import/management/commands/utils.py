"""Utils for reading Woocommerce subscriptions."""
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Set
import logging
import re
import time

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry  # noqa: F401
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import make_aware as _make_aware
from phpserialize import dumps, loads
from wordpress.models import (
    Post,
    User,
    WpWoocommerceTaxRates,
)
import dateutil.parser
import pytz.exceptions

from looper.models import (
    Address,
    Order,
    PaymentMethod,
    Transaction,
)
from looper.money import Money
from looper.taxes import TaxType  # , Taxable

from common.markdown import sanitize
from users.blender_id import BIDSession

UserModel = get_user_model()
bid = BIDSession()
logger = logging.getLogger('store_import')
wp_tax_rates = None
re_order_tax_item_name = re.compile(r'([A-Z]{2})-VAT\s+(\d{2})%')
re_order_tax_item_name_missing_rate = re.compile(r'([A-Z]{2})-VAT')


SUBSCRIPTION_PRODUCT_IDS = ('14', '4164')
ORDER_STATUS = {
    'wc-completed': 'paid',
    'wc-pending': 'created',
    'wc-failed': 'failed',
    'wc-on-hold': 'created',  # FIXME(anna): not sure what order on-hold means here
    'wc-cancelled': 'cancelled',
    'wc-refunded': 'refunded',
}
SUBSCRIPTION_STATUS = (
    # 'trash',
    'wc-active',
    # 'wc-auto-draft',
    # 'wc-cancelled',
    # 'wc-expired',
    'wc-on-hold',
    'wc-pending',
    'wc-pending-cancel',
    # 'wc-switched',
    # 'wp-cancelled',
)
COUNTRY_CODES_IGNORE_MISSING_TAX = ('CH', 'NO', 'GB')
# Used for validating tax items on the orders
EEA_COUNTRY_CODES = (
    'AL',
    'AT',
    'BA',
    'BE',
    'BG',
    'CH',
    'CY',
    'DE',
    'DK',
    'EE',
    'ES',
    'FI',
    'FR',
    'GB',
    'GR',
    'HR',
    'HU',
    'IE',
    'IS',
    'IT',
    'LT',
    'LV',
    'MK',
    'MT',
    'NL',
    'NO',
    'PL',
    'PT',
    'RO',
    'RS',
    'SE',
    'SI',
    # Added based on latest https://ec.europa.eu/taxation_customs/
    'CZ',
    'LU',
    'SK',
)


def make_aware(value):
    """Catch AmbiguousTimeError and try with a DST flag."""
    try:
        return _make_aware(value)
    except (pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError):
        # , get_current_timezone(), is_dst=False ?
        return _make_aware(value, is_dst=False)


def _subscription_status(wp_status: str):
    status = 'on-hold'
    if 'active' in wp_status:
        status = 'active'
    elif 'hold' in wp_status:
        status = 'on-hold'
    elif 'pending' in wp_status and 'cancel' in wp_status:
        status = 'pending-cancellation'
    return status


def _convert_bytes_dict(data):
    if isinstance(data, bytes):
        return data.decode('utf-8')
    if isinstance(data, dict):
        return dict(map(_convert_bytes_dict, data.items()))
    if isinstance(data, tuple):
        return map(_convert_bytes_dict, data)
    return data


def _loads(value):
    return loads(value.encode() if not isinstance(value, bytes) else value)


def _get_braintree_payment_tokens_data(wp_user: Post) -> dict:
    default = dumps({})
    _ = _get_meta_value(wp_user, '_wc_braintree_credit_card_payment_tokens', default)
    wc_cc_payment_tokens = _loads(_)
    _ = _get_meta_value(wp_user, '_wc_braintree_paypal_payment_tokens', default)
    wc_pp_payment_tokens = _loads(_)
    logger.debug('BT PP tokens: %s, BT CC tokens: %s', wc_pp_payment_tokens, wc_cc_payment_tokens)
    return {
        **_convert_bytes_dict(wc_cc_payment_tokens),
        **_convert_bytes_dict(wc_pp_payment_tokens),
    }


def _recognisable_name_pp(payer_email):
    return f'PayPal account {payer_email}'


def _recognisable_name_cc(card_type: str, four: str):
    card_type = card_type.capitalize()
    return f'{card_type} credit card ending in {four}'


def _construct_billing_address(wp_post: Post, address: Optional[Address] = None):
    if address is None:
        address = Address()
    _print_meta(wp_post)
    address.street_address = _get_meta_value(wp_post, 'billing_address_1', '')
    address.extended_address = _get_meta_value(wp_post, 'billing_address_2', '')
    address.locality = _get_meta_value(wp_post, 'billing_city', '')
    address.country = _get_meta_value(wp_post, 'billing_country')
    address.region = _get_meta_value(wp_post, 'billing_state', '')
    address.postal_code = _get_meta_value(wp_post, 'billing_postcode', '')
    address.company = _get_meta_value(wp_post, 'billing_company', '')
    first_name = _get_meta_value(wp_post, 'billing_first_name', '')
    last_name = _get_meta_value(wp_post, 'billing_last_name', '')
    if first_name or last_name:
        address.full_name = f'{first_name} {last_name}'.strip()
    return address


def _payment_methods_from_user(wp_user: Post, user: User) -> List[PaymentMethod]:
    payment_methods = []
    _print_meta(wp_user)
    for token, data in _get_braintree_payment_tokens_data(wp_user).items():
        logger.debug('Braintree token: %s, %s', token, data)
        _type = data['type']
        if _type == 'credit_card':
            method_type = 'cc'
            name = _recognisable_name_cc(card_type=data['card_type'], four=data['last_four'])
        elif _type == 'paypal':
            method_type = 'pa'
            name = _recognisable_name_pp(payer_email=data['payer_email'])
        else:
            raise Exception(f'Unknown payment method type {data}')
        payment_methods.append(
            PaymentMethod(
                user=user,
                created_at=wp_user.date_registered,
                updated_at=wp_user.date_registered,
                method_type=method_type,
                token=token,
                recognisable_name=name,
            )
        )
    return payment_methods


def _get_cc_last_four(wp_order: Post) -> str:
    return _get_meta_value_any_of(
        wp_order,
        '_wc_braintree_credit_card_account_four',
        '_wc_braintree_card_last_four',
        default='',
    )


def _get_cc_type(wp_order: Post) -> str:
    return _get_meta_value_any_of(
        wp_order,
        '_wc_braintree_credit_card_card_type',
        '_wc_braintree_card_type',
        default='',
    )


def _payment_method_from_order(wp_order: Post, user: User) -> PaymentMethod:
    method_type = None
    token = _get_payment_token(wp_order)
    _print_meta(wp_order)
    assert token, f'Unable to find a payment in {wp_order}'
    card_type = _get_cc_type(wp_order)
    paypal_email = _get_meta_value(wp_order, '_wc_braintree_paypal_payer_email', '')
    payment_method = _get_meta_value_any_of(
        wp_order, '_payment_method', '_wcs_migrated_recurring_payment_method', default=''
    )
    if card_type:
        method_type = 'cc'
        four = _get_cc_last_four(wp_order)
        name = _recognisable_name_cc(card_type=card_type, four=four)
    elif paypal_email:
        method_type = 'pa'
        name = _recognisable_name_pp(paypal_email)
    elif payment_method == 'bacs':
        method_type = 'ba'
        name = ''
    else:
        msg = f'Unable to construct payment method from {wp_order}'
        # raise Exception(msg)
        logger.debug(msg)
        return None
    return PaymentMethod(
        user=user,
        created_at=wp_order.post_date,
        updated_at=wp_order.post_date,
        method_type=method_type,
        token=token,
        recognisable_name=name,
    )


def _print_meta(post, ignore=('shipping',)):
    _type = getattr(post, 'post_type', post.__class__.__name__)
    for k in post._meta.get_fields():
        name = k.name
        if name == 'parent':
            name = 'parent_id'
        logger.debug(f'Type: {_type} ID: {post.id}   | {k.name}: {getattr(post, name, "?")}')
    if not hasattr(post, 'meta'):
        return
    for _ in post.meta.all():
        if any(ignored_substr in _.key for ignored_substr in ignore):
            continue
        logger.debug(f'Type: {_type} ID: {post.id}   | key: {_.key}      | {_.value}')


def _get_meta_value(wp, key, default=None, debug=False):
    for meta in wp.meta.all():
        if meta.key == key:
            return meta.value
    # Try with an underscore, because designing a database schema that makes sense is nobody's job
    if not key.startswith('_'):
        for meta in wp.meta.all():
            if meta.key == f'_{key}':
                return meta.value
    if default is None:
        if debug:
            _print_meta(wp)
        raise KeyError(f'{key} not found in {wp}')
    return default


def _get_meta_value_any_of(wp, *keys, default=None):
    for k in keys:
        v = _get_meta_value(wp, k, default=default)
        if v:
            return v
    if default is None:
        raise KeyError(f'None of {keys} found in {wp}')


def get_wp_users(posts: List[Post]):
    """Retrieve all Wordpress users linked to the given posts."""
    wp_user_ids = set()
    for post in posts:
        wp_user_ids.add(_get_meta_value(post, '_customer_user'))

    logger.info('Found %s user IDs for %s subscriptions', len(wp_user_ids), posts.count())
    return {
        user.id: user
        for user in User.objects.prefetch_related('meta').filter(
            id__in=wp_user_ids,
        )
    }


def _get_subscriptions(**filters):
    # logger.debug('Fetching subscriptions, filters: %s', filters)
    return (
        Post.objects.select_related('parent')
        .prefetch_related('meta')
        .filter(post_type='shop_subscription', status__in=SUBSCRIPTION_STATUS, **filters)
        .order_by('-id')
    )


def _get_subscriptions_orders(subscription_ids: Set[int]) -> Dict[int, List[Post]]:
    start_t = time.time()
    wp_orders = Post.objects.prefetch_related('meta', 'order_items').filter(
        post_type__in=('shop_order', 'show_order_refund'),
        meta__key='_subscription_renewal',
        meta__value__isnull=False,
        meta__value__in={str(_) for _ in subscription_ids},
    )
    wp_orders_per_subscription_id = {}
    unexpected_order_statuses = set()
    max_id = 0
    for o in wp_orders.all():
        _subscription_id = int(_get_meta_value(o, '_subscription_renewal'))
        if o.pk > max_id:
            max_id = o.pk
        if o.status not in ORDER_STATUS:
            unexpected_order_statuses.add(o.status)
        if _subscription_id not in wp_orders_per_subscription_id:
            wp_orders_per_subscription_id[_subscription_id] = []
        wp_orders_per_subscription_id[_subscription_id].append(o)
    if unexpected_order_statuses:
        logger.debug('Unexpected order statuses: %s', unexpected_order_statuses)
    logger.info('Took %s to collect all the orders, max ID: %s', time.time() - start_t, max_id)
    return wp_orders_per_subscription_id


def _get_subscriptions_order_numbers(subscription_ids: Set[int]) -> Dict[str, int]:
    wp_orders = Post.objects.prefetch_related('meta').filter(
        post_type__in=('shop_order', 'show_order_refund'),
        meta__key='_subscription_renewal',
        meta__value__isnull=False,
        meta__value__in={str(_) for _ in subscription_ids},
    )
    count_per_order_number = {}
    for o in wp_orders.all():
        number = _get_meta_value(o, '_order_number_formatted', '')
        if number not in count_per_order_number:
            count_per_order_number[number] = 0
        count_per_order_number[number] += 1
    return count_per_order_number


def _get_line_item(wc_order_items, item_type: str, item_name=None, **meta):
    item = next(
        (
            _
            for _ in wc_order_items
            if _.order_item_type == item_type
            and (item_name is None or _.order_item_name.startswith(item_name))
        ),
        None,
    )
    assert item, f'Missing line item {item_type}'
    for k, expected_values in meta.items():
        value = _get_meta_value(item, k)
        if not isinstance(expected_values, (tuple, list)):
            expected_values = [expected_values]
        assert any(
            expected_value == value for expected_value in expected_values
        ), f'Line item {k} not one of {expected_values}, {value} instead'
    return item


def _is_paypal_ipn(wp: Post):
    return _get_meta_value(wp, 'PayPal Payment type', '') != ''


def _get_payment_token(wp_subscription_or_order: Post) -> Optional[str]:
    token = _get_meta_value_any_of(
        wp_subscription_or_order,
        '_wc_braintree_paypal_payment_token',
        '_wc_braintree_credit_card_payment_token',
        default='',
    )
    is_paypal_ipn = _is_paypal_ipn(wp_subscription_or_order)
    if is_paypal_ipn and not token:
        return None
    _payment_method_title = _get_meta_value(wp_subscription_or_order, '_payment_method_title', '')
    is_direct_bank_transfer = _payment_method_title.lower() == 'Direct Bank Transfer'.lower()
    if not token and is_direct_bank_transfer:
        token = 'bank'
    return token


def _meta_to_money(wp, currency, meta_key):
    return Money(currency, int(Decimal(_get_meta_value(wp, meta_key)) * 100))


def _get_currency(wp: Post) -> str:
    return _get_meta_value(wp, '_order_currency')


def _meta_to_datetime(wp: Post, meta_key, default=None):
    value = _get_meta_value(wp, meta_key, default=default)
    if not value or str(value) == '0':
        return None
    try:
        return dateutil.parser.parse(value) if value else None
    except Exception as e:
        logger.exception('Unable to parse a datetime: %s, %s', value, e)
        raise


def _get_or_parse_taxes(wc_order_items) -> Tuple[str, Decimal, str, bool]:
    wp_tax_rates = get_wp_tax_rates()

    tax_items = [_ for _ in wc_order_items if _.order_item_type == 'tax']
    taxes = []
    for tax_item in tax_items:
        _print_meta(tax_item)
        tax_rate_name = tax_item.order_item_name
        rate_id = _get_meta_value(tax_item, 'rate_id')
        if rate_id == 'zero-rated':  # TODO(anna) check: should only be present with VATINs?
            # tax_rate = 0
            # tax_country = ''
            # tax_class = ''
            continue
        _tax_rate = wp_tax_rates.get(int(rate_id))
        if _tax_rate:
            logger.debug('Checking tax rate %s', _tax_rate)
            _print_meta(_tax_rate)
            tax_country = _tax_rate.tax_rate_country
            tax_rate = _tax_rate.tax_rate
            tax_class = _tax_rate.tax_rate_class
            tax_rate_name = _tax_rate.tax_rate_name
        else:
            # Tax rate might have been removed, try to parse it from the tax item
            logger.debug('Tax rate ID=%s does not exist, order pk=%s', rate_id, tax_item.order_id)
            tax_class = ''  # FIXME: what to do if unable to figure out tax class at this point?
            # order_item_name: GB-VAT 20%-1
            parsed_tax_name = re_order_tax_item_name.match(tax_rate_name)
            # order_item_name: GB-VAT-1
            parsed_tax_name_no_rate = re_order_tax_item_name_missing_rate.match(tax_rate_name)
            if parsed_tax_name:
                tax_country, tax_rate = parsed_tax_name.groups()
            elif parsed_tax_name_no_rate:
                logger.debug(
                    'Tax rate ID=%s does not exist, order pk=%s, unable to parse its rate "%s"',
                    rate_id,
                    tax_item.order_id,
                    tax_rate_name,
                )
                (tax_country,) = parsed_tax_name_no_rate.groups()
                tax_rate = 0
            else:
                logger.debug(
                    'Tax rate ID=%s does not exist, order pk=%s, unable to parse:"%s"',
                    rate_id,
                    tax_item.order_id,
                    tax_rate_name,
                )
                continue
        taxes.append(
            (
                tax_country,
                Decimal(tax_rate),
                tax_class,  # Important: must be digital-goods
                'VAT' in tax_rate_name,
            )
        )
    return taxes


def _get_order_vat_exempt(wp_order: Post) -> bool:
    return _get_meta_value(wp_order, 'is_vat_exempt', '') == 'yes' or bool(
        _get_vat_number(wp_order)
    )


def _get_tax_type(wp: Post):
    currency = _get_currency(wp)
    tax = _meta_to_money(wp, currency, 'order_tax')

    tax_country = _get_meta_value(wp, 'billing_country', '')
    is_eea = tax_country in EEA_COUNTRY_CODES
    is_vat_exempt = _get_order_vat_exempt(wp)
    # TODO(anna): how to tell if an order has reverse-charged VAT?
    has_reverse_charge = is_vat_exempt and is_eea

    tax_type = TaxType.NO_CHARGE
    if tax._cents != 0:
        if has_reverse_charge:
            logger.debug(
                '%s (%s) is reverse-charged but has non-zero tax %s',
                wp,
                tax_country,
                tax,
            )
        tax_type = TaxType.VAT_CHARGE
    elif has_reverse_charge:
        tax_type = TaxType.VAT_REVERSE_CHARGE
    elif is_eea:
        if tax_country not in COUNTRY_CODES_IGNORE_MISSING_TAX:
            logger.debug(
                '%s (%s) is neither VAT exempt not has a tax but is for EEA country',
                wp,
                tax_country,
            )
    return tax_type, tax_country


def _get_tax_info(wc_order_items, wp_order):
    tax_type, tax_country = _get_tax_type(wp_order)
    tax_rate = Decimal(0)

    tax_country = _get_meta_value(wp_order, 'billing_country', '')
    is_eea = tax_country in EEA_COUNTRY_CODES
    is_vat_exempt = _get_order_vat_exempt(wp_order)

    # Try to recover order's tax rate for posterity it looks like VAT applies for this "order":
    if tax_type == TaxType.VAT_CHARGE:
        _tax_rates = _get_or_parse_taxes(wc_order_items)
        if not _tax_rates:
            if not is_vat_exempt and is_eea:
                logger.debug(
                    'Missing VAT on order pk=%s, billing country %s',
                    wp_order.pk,
                    tax_country,
                )
            return tax_type, tax_country, tax_rate

        for tax_country, tax_rate, tax_class, looks_like_vat_charge in _tax_rates:
            if tax_class == 'digital-goods':
                logger.debug(
                    'Tax rate found: %s, %s, %s, %s',
                    tax_country,
                    tax_rate,
                    tax_class,
                    looks_like_vat_charge,
                )
    return tax_type, tax_country, tax_rate


def _print_comments(wp: Post):
    for comment in wp.comments.all():
        logger.debug(comment)


def _has_only_subscription_line_item(wc_order_items) -> bool:
    return (
        len([_ for _ in wc_order_items if _.order_item_type == 'line_item']) == 1
        and len(
            [_ for _ in wc_order_items if _.order_item_name.startswith('Blender Cloud Membership')]
        )
        == 1
    )


def _get_vat_number(wp: Post) -> str:
    vat_number_validated = (
        _get_meta_value(wp, 'vat_number_validated', '') == 'valid'
        or _get_meta_value(wp, 'Valid EU VAT Number', '') == 'true'
    )
    vat_number = (
        _get_meta_value_any_of(wp, 'vat_number', 'VAT Number', default='')
        if vat_number_validated
        else ''
    )
    if vat_number:
        assert vat_number_validated, f'{wp} got a VATIN "{vat_number}" but no validation flags'
    return vat_number.strip().replace(' ', '') if vat_number else ''


def _get_transaction_date(wp_order: Post, order: Order):
    _date = _meta_to_datetime(wp_order, '_wc_braintree_paypal_trans_date', '') or _meta_to_datetime(
        wp_order, '_wc_braintree_credit_card_trans_date', ''
    )
    if _date:
        _date = make_aware(_date)
    else:
        _date = order.paid_at or order.created_at
    return _date


def get_wp_tax_rates() -> Dict[int, WpWoocommerceTaxRates]:
    """Retrieve all the tax rates known to WP."""
    global wp_tax_rates

    if not wp_tax_rates:
        start_t = time.time()
        wp_tax_rates = {_.pk: _ for _ in WpWoocommerceTaxRates.objects.all()}
        logger.info('Fetched Wordpress tax rates in %s', time.time() - start_t)
    return wp_tax_rates


def _get_subscription_collection_method(wp: Post) -> str:
    if _get_meta_value(wp, '_requires_manual_renewal') == 'true':
        return 'manual'
    return 'automatic'


def _get_order_collection_method(wp: Post) -> str:
    _requires_manual_renewal = _get_meta_value_any_of(
        wp,
        '_requires_manual_renewal',
        '_wcs_requires_manual_renewal',
        default='',
    )
    if _requires_manual_renewal:
        if _requires_manual_renewal == 'true':
            return 'manual'
    return ''


def _get_subscription_line_item(wc_order_items):
    try:
        return _get_line_item(
            wc_order_items,
            'line_item',
            'Blender Cloud Membership',
            _product_id=SUBSCRIPTION_PRODUCT_IDS,
        )
    except AssertionError:
        return None


def _get_admin_user(bid, wp_user: Post) -> Optional[User]:
    oauth_user_id = _get_meta_value(wp_user, 'blender_id', '')
    if oauth_user_id:
        try:
            oauth_user_info = bid.get_oauth_user_info(oauth_user_id)
            return oauth_user_info.user
        except Exception:
            return

    email = _get_meta_value(wp_user, 'email', '')
    if email:
        return UserModel.objects.filter(email=email).first()


def _construct_log_entries_from_comments(
    wp: Post, instance, wp_users, action_flag=CHANGE
) -> List[LogEntry]:
    entries = []
    _print_comments(wp)
    content_type_id = ContentType.objects.get_for_model(type(instance)).pk
    object_repr = str(instance)
    for comment in wp.comments.all():
        message = comment.content
        wp_user = None
        if comment.user_id:
            if comment.user_id not in wp_users:
                wp_user = User.objects.prefetch_related('meta').filter(id=comment.user_id).first()
                if wp_user:
                    wp_users[comment.user_id] = wp_user
            else:
                wp_user = wp_users[comment.user_id]

        user = None
        if wp_user:
            user = _get_admin_user(bid, wp_user)
        else:
            user = UserModel.objects.filter(email=comment.author_email).first()
        message = sanitize(message)
        entries.append(
            dict(
                user_id=user.pk if user else settings.LOOPER_SYSTEM_USER_ID,
                content_type_id=content_type_id,
                object_id=str(instance.pk),
                object_repr=object_repr[:200],
                # ADDITION is useless because change_message is ignored when such entry is displayed
                action_flag=action_flag,
                action_time=comment.post_date,
                change_message=message,
            )
        )
    return entries


def _construct_failed_transactions_from_comments(wp_order: Post, order: Order) -> List[Transaction]:
    # Try to parse it out of the comments then
    failed_transactions = []
    comments_with_transaction_id = wp_order.comments.filter(content__contains='Transaction ID')
    for comment in comments_with_transaction_id:
        if 'failed' not in comment.content.lower():
            continue
        transaction_ids = re.findall(r'Transaction ID ([^ ]+)\)', comment.content)
        if not transaction_ids:
            continue

        failure_codes = re.findall(r'status code (\d+)', comment.content, re.I)
        failure_code = failure_codes[0] if failure_codes else ''
        if not failure_code:
            continue
        transaction_id = transaction_ids[0]
        failure_messages = re.findall(r'status code \d+: ([^(]+)', comment.content, re.I)
        failure_message = failure_messages[0].strip() if failure_messages else ''
        failed_transactions.append(
            Transaction(
                created_at=comment.post_date,
                updated_at=comment.post_date,
                user=order.user,
                order=order,
                payment_method=order.payment_method,
                transaction_id=transaction_id,
                failure_code=failure_code,
                failure_message=failure_message,
                currency=order.currency,
                amount=order.price,
                paid=False,
                status='failed',
            )
        )
    return failed_transactions


def _equal_allow_one_cent(money1, money2) -> bool:
    is_same_currency = money1.currency == money2.currency
    cents_difference = abs(money1._cents - money2._cents)
    is_off_one_cent = cents_difference == 1
    if is_same_currency and is_off_one_cent:
        logger.debug('One-cent error: %s != %s', money1, money2)
    return is_same_currency and cents_difference <= 1
