"""Custom validators for subscription-related forms."""
import logging
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from stdnum.eu import vat
import stdnum.exceptions

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
with open(settings.BASE_DIR / 'subscriptions' / 'common_email_domains.txt') as f:
    domains = set(_.strip() for _ in f.readlines())
    common_email_domains = '|'.join(domains)
re_common_email_domain = re.compile(f'^({common_email_domains})$', re.I)
re_valid_invoice_reference = re.compile('^[-_ #0-9a-z]*$', re.I)


class VATINValidator:
    """A validator for VAT identification numbers.

    Currently only supports European VIES VAT identification numbers.
    See See https://en.wikipedia.org/wiki/VAT_identification_number
    """

    messages = {
        'country_code': _(
            'VAT identification number must start with a valid 2-letter country code.'
        ),
        'vatin': _('%(vatin)s is not a valid VAT identification number.'),
        'vies': _('%(vatin)s is not a registered VAT identification number.'),
        'unavailable': _('Unable to verify VAT identification number. Please try again later.'),
    }

    def __call__(self, value):
        """Validate the given value as VATIN."""
        try:
            vat_number = vat.validate(value)
        except stdnum.exceptions.ValidationError:
            raise ValidationError(
                self.messages['vatin'], code='vat_number', params={'vatin': value}
            )
        country_code = vat.guess_country(vat_number)
        if not country_code:
            raise ValidationError(
                self.messages['country_code'],
                code='vat_number',
            )

        # Attempt to validate the number against VIES
        is_valid = False
        try:
            vies_response = vat.check_vies(vat_number)
            logger.debug('Got response from VIES: %s', vies_response)
            is_valid = vies_response.valid
        except Exception:
            logger.exception('Unabled to verify the VAT identification number')
            raise ValidationError(self.messages['unavailable'], code='vat_number')

        if not is_valid:
            raise ValidationError(self.messages['vies'], code='vat_number', params={'vatin': value})


def _is_valid_domain(domain: str) -> bool:
    if len(domain) > 255:
        return False
    parts = domain.split('.')
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return len(parts) > 1 and all(allowed.match(x) for x in parts)


def _is_common_email_domain(value: str) -> str:
    return re_common_email_domain.match(value)


def validate_email_domain(value: str) -> str:
    """Ensure the given value is not an invalid host name or a common email domain name."""
    value = value.lower().strip()
    if value[-1] == ".":
        value = value[:-1]  # strip exactly one dot from the right, if present
    if not _is_valid_domain(value):
        raise ValidationError('Must be a valid domain name')
    if _is_common_email_domain(value):
        raise ValidationError('Domains of common email providers are not allowed')
    return value


def validate_invoice_reference(value: str) -> str:
    """Ensure the given value is an acceptible invoice reference (Order.external_reference)."""
    if not re_valid_invoice_reference.match(value):
        raise ValidationError(
            'Only the following are allowed: '
            'letters (A-Z, a-z), digits (0-9), -, _, # and blank space.'
        )
    return value
