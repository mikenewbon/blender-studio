from django.contrib import admin
from django.db.models import QuerySet
from django.db.models import Value, Case, When
from django.http.request import HttpRequest

from comments import models
from common.mixins import AdminUserDefaultMixin
from common.types import assert_cast


@admin.register(models.Comment)
class CommentAdmin(AdminUserDefaultMixin, admin.ModelAdmin):
    list_display = ['__str__', 'comment_under']

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[models.Comment]':
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _comment_under=Case(
                When(section__isnull=False, then='section__name'),
                When(asset__isnull=False, then='asset__name'),
                default=Value(''),
            )
        )
        return queryset

    def comment_under(self, obj: models.Comment) -> str:
        return assert_cast(str, obj._comment_under)  # type: ignore[attr-defined]
