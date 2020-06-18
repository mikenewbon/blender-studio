from django.contrib import admin

from assets.models import assets, licenses, storages


@admin.register(licenses.License)
class LicenseAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(assets.StaticAsset)
admin.site.register(assets.Image)
admin.site.register(assets.Video)
admin.site.register(storages.StorageBackend)
