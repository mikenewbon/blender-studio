from django.contrib import admin
from django.db.models import QuerySet
from django.db.models import Value, Case, When, Exists, OuterRef
from django.db.models.fields import BooleanField, CharField
from django.http.request import HttpRequest

from comments import models
from common.mixins import AdminUserDefaultMixin
from common.types import assert_cast


@admin.register(models.Comment)
class CommentAdmin(AdminUserDefaultMixin, admin.ModelAdmin):
    list_display = ['__str__', 'comment_under', 'has_replies', 'is_deleted']
    list_filter = ['date_created', 'date_deleted']
    search_fields = [
        'message',
        'asset__name',
        'section__name',
        'post__slug',
        'user__username',
        'user__email',
    ]
    readonly_fields = ['date_created', 'date_updated', 'date_deleted']
    raw_id_fields = ['reply_to']

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[models.Comment]':
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _comment_under=Case(
                When(section__isnull=False, then='section__name'),
                When(asset__isnull=False, then='asset__name'),
                When(post__isnull=False, then='post__slug'),
                default=Value(''),
                output_field=CharField(),
            ),
            _has_replies=Exists(models.Comment.objects.filter(reply_to_id=OuterRef('pk'))),
            _is_deleted=Case(
                When(date_deleted__isnull=False, then=Value(True)),
                default=False,
                output_field=BooleanField(),
            ),
        )
        return queryset

    def comment_under(self, obj: models.Comment) -> str:
        return assert_cast(str, getattr(obj, '_comment_under'))

    def has_replies(self, obj: models.Comment) -> bool:
        return assert_cast(bool, getattr(obj, '_has_replies'))

    def is_deleted(self, obj: models.Comment) -> bool:
        return assert_cast(bool, getattr(obj, '_is_deleted'))


@admin.register(models.Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'comment']
    search_fields = [
        'comment__message',
        'user__email',
        'user__username',
    ]
    readonly_fields = ['date_created', 'date_updated', 'user', 'comment']
