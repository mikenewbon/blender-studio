"""Custom validators for subscription-related forms."""
import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from stdnum.eu import vat
import stdnum.exceptions

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
