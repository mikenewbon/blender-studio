from django.contrib import admin

from profiles.models import Notification
from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Configure Notification admin."""

    search_fields = ['user__username', 'user__email', 'user__profile__full_name']
    list_display = ['__str__', 'user', 'action']
    raw_id_fields = ['user', 'action']


@admin.register(OAuthUserInfo)
class OAuthUserInfoAdmin(admin.ModelAdmin):
    """Configure OAuthUserInfo admin, because blender_id_oauth_client doesn't."""

    search_fields = ['user__email', 'user__username']
    list_display = ['user', 'oauth_user_id']
    raw_id_fields = ['user']


admin.site.unregister(OAuthToken)


@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    """Configure OAuthToken admin, because otherwise it tried to load all users."""

    search_fields = ['user__email', 'user__username']
    list_display = ['user', 'oauth_user_id']
    raw_id_fields = ['user']
