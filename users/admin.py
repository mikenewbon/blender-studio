from django.contrib import admin
from django.contrib.auth import get_user_model, admin as auth_admin
from django.utils.translation import gettext_lazy as _

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken
from users.models import Notification


@admin.register(get_user_model())
class UserAdmin(auth_admin.UserAdmin):
    def has_add_permission(self, request):
        """User records are managed by Blender ID, so no new user should be added here."""
        return False

    list_display_links = ('full_name', 'username')
    list_filter = auth_admin.UserAdmin.list_filter + (
        'is_subscribed_to_newsletter',
        'date_deletion_requested',
    )
    list_display = (
        ['full_name']
        + [_ for _ in auth_admin.UserAdmin.list_display if _ not in ('first_name', 'last_name')]
        + ['is_active', 'deletion_requested']
    )
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            _('Personal info'),
            {'fields': ('full_name', 'image', 'email', 'is_subscribed_to_newsletter', 'badges')},
        ),
        (
            _('Permissions'),
            {
                'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            },
        ),
        (
            _('Important dates'),
            {'fields': ('last_login', 'date_joined', 'date_deletion_requested')},
        ),
    )
    readonly_fields = ('date_deletion_requested',)

    def deletion_requested(self, obj):
        """Display yes/no icon status of deletion request."""
        return obj.date_deletion_requested is not None

    deletion_requested.boolean = True


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
