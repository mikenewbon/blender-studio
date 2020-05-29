from django.contrib import admin

from assets.models import assets, licenses

admin.site.register(assets.Asset)
admin.site.register(assets.Image)
admin.site.register(assets.Video)
admin.site.register(assets.File)
admin.site.register(licenses.License)
