from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Meta:
        db_table = 'auth_user'

    email = models.EmailField(_('email address'), blank=False, null=False, unique=True)
