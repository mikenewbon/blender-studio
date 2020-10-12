from django.contrib import admin

from common.mixins import AdminUserDefaultMixin
from static_assets.models import static_assets, licenses, storages


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
    readonly_fields = ['play_count']


@admin.register(static_assets.StaticAsset)
class StaticAssetAdmin(AdminUserDefaultMixin, admin.ModelAdmin):
    inlines = [ImageInline, VideoInline]
    fieldsets = (
        (
            None,
            {
                'fields': [
                    'source',
                    'original_filename',
                    'size_bytes',
                    'source_type',
                    'user',
                    'author',
                    'license',
                    'thumbnail',
                    'date_created',
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
    list_filter = ['source_type', 'user', 'author']
    search_fields = [
        'original_filename',
        'user__first_name',
        'user__last_name',
        'author__first_name',
        'author__last_name',
        'source_type',
    ]
    readonly_fields = ['original_filename', 'size_bytes', 'date_created']


admin.site.register(storages.StorageLocation)
