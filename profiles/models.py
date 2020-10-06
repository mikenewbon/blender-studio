import logging

import botocore.exceptions
import requests

from django import urls
from django.contrib.auth.models import User
from django.db import models

from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from profiles.blender_id import BIDSession

bid = BIDSession()
logger = logging.getLogger(__name__)


class Profile(mixins.CreatedUpdatedMixin, models.Model):
    """Store additional Profile data, such as avatar and full name."""

    user = models.OneToOneField(
        User, primary_key=True, on_delete=models.CASCADE, related_name='profile'
    )
    full_name = models.CharField(max_length=255, blank=True, default='')
    avatar = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True)

    def get_absolute_url(self):
        """Return absolute URL of a Profile."""
        return urls.reverse('profile_detail', kwargs={'pk': self.pk})

    def __str__(self) -> str:
        return f'Profile {self.user}'

    def copy_avatar_from_blender_id(self):
        """
        Attempt to retrieve an avatar from Blender ID and save it into our storage.

        If either OAuth info or Blender ID service isn't available, log an error and return.
        """
        if not hasattr(self.user, 'oauth_info'):
            logger.error(f'Cannot copy avatar from Blender ID: {self} is missing OAuth info')
            return
        oauth_info = self.user.oauth_info
        try:
            name, content = bid.get_avatar(oauth_info.oauth_user_id)
            self.avatar.save(name, content, save=True)
            logger.info(f'Avatar updated for {self}')
        except requests.HTTPError:
            logger.exception(f'Failed to retrieve an avatar for {self} from Blender ID')
        except botocore.exceptions.BotoCoreError:
            logger.exception(f'Failed to store an avatar for {self}')
        except Exception:
            logger.exception(f'Failed to copy avatar for {self}')
