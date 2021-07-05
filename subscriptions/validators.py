"""Custom validators for subscription-related forms."""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from stdnum.eu import vat
import stdnum.exceptions


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
