from typing import Optional

from django.contrib import admin

from comments import models
from common.mixins import AdminUserDefaultMixin


@admin.register(models.Comment)
class CommentAdmin(AdminUserDefaultMixin, admin.ModelAdmin):
    list_display = ['__str__', 'comment_under']

    def comment_under(self, obj: models.Comment) -> Optional[str]:
        commented_entity = obj.section.first() or obj.asset.first()
        if commented_entity:
            return f"<{commented_entity._meta.model_name}> {commented_entity}"

        return None
