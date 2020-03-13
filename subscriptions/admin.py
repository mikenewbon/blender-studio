from django.contrib import admin

from subscriptions import models

admin.site.register(models.Subscriber)
admin.site.register(models.Organization)
admin.site.register(models.OrganizationUsers)
admin.site.register(models.SubscriptionProperties)
