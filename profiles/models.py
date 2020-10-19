from typing import Optional
import logging

from django import urls
from django.contrib.auth.models import User
from django.db import models

from common import mixins
from profiles.blender_id import BIDSession

bid = BIDSession()
logger = logging.getLogger(__name__)


class Profile(mixins.CreatedUpdatedMixin, models.Model):
    """Store additional Profile data, such as avatar and full name."""

    user = models.OneToOneField(
        User, primary_key=True, on_delete=models.CASCADE, related_name='profile'
    )
    full_name = models.CharField(max_length=255, blank=True, default='')
    is_subscribed_to_newsletter = models.BooleanField(default=False)

    def get_absolute_url(self):
        """Return absolute URL of a Profile."""
        return urls.reverse('profile_detail', kwargs={'pk': self.pk})

    def __str__(self) -> str:
        return f'Profile {self.user}'

    @property
    def image_url(self) -> Optional[str]:
        """Return a URL of the Profile image."""
        if not getattr(self.user, 'oauth_info', None) or \
                not getattr(self.user.oauth_info, 'oauth_user_id'):
            return None

        oauth_info = self.user.oauth_info
        return bid.get_avatar_url(oauth_info.oauth_user_id)
