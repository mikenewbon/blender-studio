"""Custom form widgets."""
from django import forms

from localflavor.administrative_areas import ADMINISTRATIVE_AREAS


class RegionSelect(forms.Select):
    """Adds regions per country data."""

    template_name = 'subscriptions/widgets/region_select.html'

    def get_context(self, name, value, attrs):
        """Add regions/states/provinces data to the region field, to be handled by JS."""
        context = super().get_context(name, value, attrs)
        context['choices_per_country'] = ADMINISTRATIVE_AREAS
        return context
