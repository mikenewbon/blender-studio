from typing import Optional, Sequence, Union, Callable, Any, List, Tuple

from django.contrib import admin
from django.db.models import Model
from django.http.request import HttpRequest
from django.urls import reverse
from django.utils.html import format_html


class EditLinkMixin:
    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)  # type: ignore[call-arg]
        assert issubclass(
            cls, admin.options.InlineModelAdmin
        ), f'{cls.__name__} has to be a subclass of InlineModelAdmin to use the EditLinkMixin'

    def get_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Sequence[Union[Callable[..., Any], str]]:
        """Show the edit link at the top of the inline form"""
        fields = super().get_fields(request, obj)
        return [
            'get_edit_link',
            *[field for field in fields if field != 'get_edit_link'],
        ]

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Union[List[str], Tuple[str]]:
        """Display (non-editable) Edit Link field in the form"""
        readonly_fields = ['get_edit_link', *super().get_readonly_fields(request, obj)]
        return readonly_fields

    def get_edit_link(self, obj: Model) -> str:
        """Create a link in the inline to a separate form for the nested object"""
        if obj.pk:
            url = reverse(
                f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk]
            )
            return format_html(
                '<a href="{url}">Edit this {obj_name} separately</a>',
                url=url,
                obj_name=obj._meta.verbose_name,
            )
        return 'Save and continue editing to create a link'

    get_edit_link.short_description = 'Edit link'  # type: ignore[attr-defined]
