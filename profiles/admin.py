from django.contrib import admin

from profiles.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Configure Profile admin."""

    search_fields = ['full_name', 'user__username', 'user__email']
    list_display = ['__str__', 'user', 'full_name', 'image_url']
    list_filter = ['is_subscribed_to_newsletter']
