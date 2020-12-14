"""Profile activity pages, such as notifications and My activity."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from profiles.models import Profile


class IsSubscribedToNewsletterForm(ModelForm):
    """Change Profile.is_subscribed_to_newsletter flag."""

    class Meta:
        model = Profile
        fields = ['is_subscribed_to_newsletter']


class ProfileView(LoginRequiredMixin, TemplateView):
    """Template view for the profile settings."""

    template_name = 'profiles/settings/profile.html'


class BillingView(LoginRequiredMixin, TemplateView):
    """Template view for the billing/subscription settings."""

    template_name = 'profiles/settings/billing.html'


class EmailsView(LoginRequiredMixin, TemplateView):
    """Template view for the email notifications settings."""

    template_name = 'profiles/settings/emails.html'

    def get_context_data(self):
        """Add form to the context."""
        context = super().get_context_data()
        context['form'] = IsSubscribedToNewsletterForm(instance=self.request.user.profile)
        return context

    def post(self, request):
        """Change Profile.is_subscribed_to_newsletter flag of logged in user."""
        form = IsSubscribedToNewsletterForm(request.POST, instance=request.user.profile)
        form.save()
        return redirect(reverse('profile-settings-emails'))


class RolesView(LoginRequiredMixin, TemplateView):
    """Template view displaying profile roles settings."""

    template_name = 'profiles/settings/roles.html'
