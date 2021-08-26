from django.contrib import admin
from django.contrib.auth import get_user_model, admin as auth_admin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

import looper.admin
import looper.models

from blender_id_oauth_client.models import OAuthUserInfo, OAuthToken
from users.models import Notification
from training.models import progress


def user_section_progress_link(obj):
    admin_view = looper.admin._get_admin_url_name(progress.UserSectionProgress, 'changelist')
    link = reverse(admin_view) + f'?user_id={obj.pk}'
    return format_html('<a href="{}">{}</a>', link, 'View training progress for this user')


user_section_progress_link.short_description = 'Training sections progress'


def user_subscriptions_link(obj, title='View subscriptions of this user'):
    admin_view = looper.admin._get_admin_url_name(looper.models.Subscription, 'changelist')
    link = reverse(admin_view) + f'?user_id={obj.pk}'
    return format_html('<a href="{}">{}</a>', link, title)


user_subscriptions_link.short_description = 'Subscriptions'


class NumberOfSubscriptionsFilter(admin.SimpleListFilter):
    title = _('subscriptions')

    parameter_name = 'subscriptions_count'

    def lookups(self, request, model_admin):
        """Human-readable labels for filter choices."""
        return (
            ('none', 'without subscriptions'),
            ('one', 'with one subscription'),
            ('multiple', 'with more than one subscription'),
        )

    def queryset(self, request, queryset):
        """Returns the filtered queryset based on the value provided in the query string."""
        if self.value() == 'none':
            return queryset.filter(subscriptions_count=0)
        if self.value() == 'one':
            return queryset.filter(subscriptions_count=1)
        if self.value() == 'multiple':
            return queryset.filter(subscriptions_count__gt=1)


class NumberOfBraintreeCustomerIDsFilter(admin.SimpleListFilter):
    title = _('Braintree Customer IDs')

    parameter_name = 'braintreecustomerids_count'

    def lookups(self, request, model_admin):
        """Human-readable labels for filter choices."""
        return (
            ('none', 'none'),
            ('one', 'one'),
            ('multiple', 'multiple'),
        )

    def queryset(self, request, queryset):
        """Returns the filtered queryset based on the value provided in the query string."""
        if self.value() == 'none':
            return queryset.filter(braintreecustomerids_count=0)
        if self.value() == 'one':
            return queryset.filter(braintreecustomerids_count=1)
        if self.value() == 'multiple':
            return queryset.filter(braintreecustomerids_count__gt=1)


@admin.register(get_user_model())
class UserAdmin(auth_admin.UserAdmin):
    change_form_template = 'loginas/change_form.html'

    def has_add_permission(self, request):
        """User records are managed by Blender ID, so no new user should be added here."""
        return False

    def get_queryset(self, *args, **kwargs):
        """Count user subscriptions for subscription debugging purposes."""
        queryset = super().get_queryset(*args, **kwargs)
        queryset = queryset.annotate(
            subscriptions_count=Count('subscription', distinct=True),
            braintreecustomerids_count=Count(
                'gatewaycustomerid', Q(gateway__name='braintree'), distinct=True
            ),
        )
        return queryset

    def subscriptions(self, obj):
        """Return the number of subscriptions this user has and a link to them."""
        return user_subscriptions_link(obj, obj.subscriptions_count)

    list_display_links = ['username']
    list_filter = auth_admin.UserAdmin.list_filter + (
        'date_joined',
        'is_subscribed_to_newsletter',
        'date_deletion_requested',
        'last_login',
        NumberOfSubscriptionsFilter,
        NumberOfBraintreeCustomerIDsFilter,
    )

    list_display = (
        ['full_name']
        + [_ for _ in auth_admin.UserAdmin.list_display if _ not in ('first_name', 'last_name')]
        + ['is_active', 'deletion_requested', 'subscriptions']
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
            {'fields': (('date_joined', 'last_login'), 'date_deletion_requested')},
        ),
        (_('Activity'), {'fields': (user_section_progress_link, user_subscriptions_link)}),
    )
    readonly_fields = (
        'date_deletion_requested',
        'date_joined',
        'last_login',
        user_section_progress_link,
        user_subscriptions_link,
        subscriptions,
    )
    inlines = [
        looper.admin.AddressInline,
        looper.admin.CustomerInline,
        looper.admin.GatewayCustomerIdInline,
    ]
    search_fields = ['email', 'full_name', 'username']

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

    search_fields = ['user__email', 'user__username', 'oauth_user_id']
    list_display = ['user', 'oauth_user_id']
    raw_id_fields = ['user']


admin.site.unregister(OAuthToken)


@admin.register(OAuthToken)
class OAuthTokenAdmin(admin.ModelAdmin):
    """Configure OAuthToken admin, because otherwise it tried to load all users."""

    search_fields = ['user__email', 'user__username']
    list_display = ['user', 'oauth_user_id']
    raw_id_fields = ['user']
