"""Custom template utilities for formatting subscriptions."""
from typing import Optional, Union

from django import template

from looper.models import PlanVariation, Subscription
import looper.money
import looper.taxes

import subscriptions.queries

register = template.Library()


@register.filter
def renewal_period(variation: Union[PlanVariation, Subscription]) -> str:
    """Format plan variation's renewal period in a human-readable manner.

    Also works for Subscriptions, because they share the same set of fields.
    """
    if variation.interval_unit == 'month':
        if variation.interval_length == 1:
            return 'monthly'
        if variation.interval_length == 3:
            return 'quarterly'
        if variation.interval_length == 6:
            return 'half-yearly'
    elif variation.interval_unit == 'year':
        if variation.interval_length == 1:
            return 'yearly'
    return 'every\u00A0{variation.interval_length}\u00A0{variation.interval_unit}s'


@register.filter
def recurring_pricing(variation: PlanVariation, money: Optional[looper.money.Money] = None) -> str:
    """Format plan variation's recurring pricing in a human-readable manner."""
    if variation is None:
        return '-'

    if not money:
        money = variation.price
    price: str = money.with_currency_symbol_nonocents()

    if variation.interval_length == 1:
        formatted_interval = variation.interval_unit
    elif variation.interval_unit == 'month':
        if variation.interval_length == 3:
            formatted_interval = 'quarter'
        elif variation.interval_length == 6:
            formatted_interval = 'half\u00A0year'
    else:
        formatted_interval = '\u00A0{variation.interval_unit}s'
    return f'{price}\u00A0/\u00A0{formatted_interval}'


@register.filter
def can_subscribe(user) -> bool:
    """True if user either has no subscriptions at all or they are all cancelled."""
    return not subscriptions.queries.has_not_yet_cancelled_subscription(user)
