from django.contrib import admin

from comments import models

admin.site.register(models.Comment)
