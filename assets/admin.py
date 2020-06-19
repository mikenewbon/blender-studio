from django.contrib import admin

from assets.models import assets, licenses, storages, AssetFileTypeChoices


@admin.register(licenses.License)
class LicenseAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


class ImageInline(admin.TabularInline):
    model = assets.Image
    extra = 0


class VideoInline(admin.TabularInline):
    model = assets.Video
    extra = 0


@admin.register(assets.StaticAsset)
class StaticAssetAdmin(admin.ModelAdmin):
    inlines = [ImageInline, VideoInline]
    fieldsets = (
        (
            None,
            {
                'fields': [
                    field.name
                    for field in assets.StaticAsset._meta.get_fields()
                    if field.editable and field.name != 'id'
                ],
            },
        ),
        (
            'If you are uploading an image or a video',
            {
                'fields': (),
                'description': 'The fields below depend on the source type of the uploaded '
                'asset. Add an <strong>Image</strong> if you are uploading an '
                'image, or a <strong>Video</strong> for video uploads.',
            },
        ),
    )
    list_filter = ['source_type', 'user', 'storage_backend__film__title']


# admin.site.register(assets.Image)
# admin.site.register(assets.Video)
admin.site.register(storages.StorageBackend)
