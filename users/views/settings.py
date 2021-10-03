"""Profile activity pages, such as notifications and My activity."""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

User = get_user_model()


class IsSubscribedToNewsletterForm(ModelForm):
    """Change User.is_subscribed_to_newsletter flag."""

    class Meta:
        model = User
        fields = ['is_subscribed_to_newsletter']


class ProfileView(LoginRequiredMixin, TemplateView):
    """Template view for the profile settings."""

    template_name = 'users/settings/profile.html'


class BillingView(LoginRequiredMixin, TemplateView):
    """Template view for the billing/subscription settings."""

    template_name = 'users/settings/billing.html'


class EmailsView(LoginRequiredMixin, TemplateView):
    """Template view for the email notifications settings."""

    template_name = 'users/settings/emails.html'

    def get_context_data(self):
        """Add form to the context."""
        context = super().get_context_data()
        context['form'] = IsSubscribedToNewsletterForm(instance=self.request.user)
        return context

    def post(self, request):
        """Change User.is_subscribed_to_newsletter flag of logged in user."""
        form = IsSubscribedToNewsletterForm(request.POST, instance=request.user)
        form.save()
        return redirect(reverse('user-settings-emails'))


class ProductionCreditsView(LoginRequiredMixin, TemplateView):
    """View to handle visibility of a user credit for the film."""

    template_name = 'users/settings/production_credits.html'

    def get_context_data(self):
        """Add credits to the context."""
        context = super().get_context_data()
        context['credits'] = self.request.user.production_credits.all()
        return context


class DeleteView(LoginRequiredMixin, TemplateView):
    """Template view where account deletion can be requested."""

    template_name = 'users/settings/delete.html'
