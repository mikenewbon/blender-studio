from django.contrib import admin

from profiles.models import Profile
from blender_id_oauth_client.models import OAuthUserInfo


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Configure Profile admin."""

    search_fields = ['full_name', 'user__username', 'user__email']
    list_display = ['__str__', 'user', 'full_name', 'image_url']
    list_filter = ['is_subscribed_to_newsletter']


@admin.register(OAuthUserInfo)
class OAuthUserInfoAdmin(admin.ModelAdmin):
    """Configure OAuthUserInfo admin, because blender_id_oauth_client doesn't."""

    search_fields = ['user__email', 'user__username']
    list_display = ['user', 'oauth_user_id']
