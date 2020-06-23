from typing import Optional, Any

from django.contrib import admin
from django.db import models
from django.db.models.fields.related import ForeignKey
from django.forms.models import ModelChoiceField
from django.http.request import HttpRequest


class CreatedUpdatedMixin(models.Model):
    class Meta:
        abstract = True

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)


class AdminUserDefaultMixin:
    """Sets the 'user' field in a form in Django Admin to the current user."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert issubclass(
            cls, admin.options.BaseModelAdmin
        ), f'{cls.__name__} has to be a subclass of BaseModelAdmin to use the UserDefaultMixin'

    def formfield_for_foreignkey(
        self, db_field: ForeignKey, request: Optional[HttpRequest], **kwargs: Any
    ) -> Optional[ModelChoiceField]:
        if db_field.name == 'user':
            kwargs['initial'] = request.user.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
