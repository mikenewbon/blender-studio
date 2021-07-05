"""Custom form fields."""
import re

from django import forms

from subscriptions.validators import VATINValidator


class VATNumberField(forms.fields.CharField):
    """Validate VAT number and strip all whitespaces from it."""

    default_validators = [VATINValidator()]

    def __init__(self, **kwargs):
        """Strip whitespaces from the value."""
        super().__init__(strip=True, **kwargs)

    def to_python(self, value):
        """Remove whitespaces that hadn't been stripped already."""
        value = super().to_python(value)
        return re.sub(r'\s+', '', value)
