from django.contrib import admin

from static_assets.models import static_assets, licenses, storages
from common.mixins import AdminUserDefaultMixin


@admin.register(licenses.License)
class LicenseAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


class ImageInline(admin.TabularInline):
    model = static_assets.Image
    show_change_link = True
    extra = 0
    max_num = 1


class VideoInline(admin.TabularInline):
    model = static_assets.Video
    show_change_link = True
    extra = 0
    max_num = 1


@admin.register(static_assets.StaticAsset)
class StaticAssetAdmin(AdminUserDefaultMixin, admin.ModelAdmin):
    inlines = [ImageInline, VideoInline]
    fieldsets = (
        (
            None,
            {
                'fields': [
                    field.name
                    for field in static_assets.StaticAsset._meta.get_fields()
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
    list_filter = ['source_type', 'user', 'author', 'storage_location__film__title']


admin.site.register(storages.StorageLocation)
