"""
Middleware for setting currency depending on the request's country.

FIXME(anna): this should move to looper unless ability to change currencies is important there.
"""
from typing import Optional

from django.http import HttpRequest
import geoip2.records

import looper.middleware

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
)
COUNTRY_CODE_USD = ('US',)


def preferred_currency_for_country_code(country_code: Optional[str] = '') -> str:
    """Return currency for the given country code."""
    if country_code in COUNTRY_CODE_USD:
        return 'USD'
    return 'EUR'


class SetCurrencyMiddleware(looper.middleware.PreferredCurrencyMiddleware):
    """Set currency depending on the geo-guessed country.

    Use our list of EEA counties to determine which countries get EUR.
    """

    def preferred_currency(
        self, request: HttpRequest, country: Optional[geoip2.records.Country]
    ) -> str:
        """Determine default currency for the given country.

        Unfortunately geoip2.models.Country isn't defined in a MyPy-compatible
        way, so we can't properly declare its type.

        :type country: geoip2.models.Country
        """
        country_code = country.iso_code if country else None
        if request.user.is_authenticated and getattr(request.user, 'customer', None):
            # If there's already a billing country set, we don't care about geo-guessing it.
            billing_country = request.user.customer.billing_address.country
            if billing_country:
                country_code = billing_country
        return preferred_currency_for_country_code(country_code)
