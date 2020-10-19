from typing import Optional, Any, Union, List, Tuple

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.db.models.base import Model
from django.http.request import HttpRequest
from sorl.thumbnail import get_thumbnail


class CreatedUpdatedMixin(models.Model):
    class Meta:
        abstract = True

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)


class AdminUserDefaultMixin:
    """On object creation, sets the 'user' field in the form in Admin to the current user.

    The field value will be displayed as read-only in the form."""

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)  # type: ignore[call-arg]
        assert issubclass(
            cls, admin.options.BaseModelAdmin
        ), f'{cls.__name__} has to be a subclass of BaseModelAdmin to use the UserDefaultMixin'

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Union[List[str], Tuple[str]]:
        """Display (non-editable) user field in the form"""
        readonly_fields = ['user', *super().get_readonly_fields(request, obj)]
        return readonly_fields

    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        """Associate created object with the current user."""
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)


class StaticThumbnailURLMixin:
    """Add `thumbnail_<size>_url` properties generating static cacheable thumbnail URLs."""

    @property
    def thumbnail_m_url(self) -> str:
        """Return a static URL to a medium-sized thumbnail."""
        return get_thumbnail(
            self.thumbnail, settings.THUMBNAIL_SIZE_M, crop=settings.THUMBNAIL_CROP_MODE
        ).url

    @property
    def thumbnail_s_url(self) -> str:
        """Return a static URL to a small thumbnail."""
        return get_thumbnail(
            self.thumbnail, settings.THUMBNAIL_SIZE_S, crop=settings.THUMBNAIL_CROP_MODE
        ).url
