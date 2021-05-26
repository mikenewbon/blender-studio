from django.contrib import admin

from subscriptions import models

admin.site.register(models.Team)
admin.site.register(models.TeamUsers)
admin.site.register(models.SubscriptionProperties)
