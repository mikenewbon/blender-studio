from django.contrib import admin

from assets.models import assets, licenses, storages

admin.site.register(assets.StaticAsset)
admin.site.register(assets.Image)
admin.site.register(assets.Video)
admin.site.register(licenses.License)
admin.site.register(storages.StorageBackend)
