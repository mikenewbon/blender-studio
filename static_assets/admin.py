from django.contrib import admin
import nested_admin

from common.mixins import AdminUserDefaultMixin
from static_assets.models import static_assets, licenses


@admin.register(licenses.License)
class LicenseAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


class ImageInline(nested_admin.NestedTabularInline):
    model = static_assets.Image
    show_change_link = True
    extra = 0
    max_num = 1


class VideoVariationInline(nested_admin.NestedTabularInline):
    model = static_assets.VideoVariation
    show_change_link = True
    extra = 0


class VideoInline(nested_admin.NestedTabularInline):
    model = static_assets.Video
    inlines = [VideoVariationInline]
    show_change_link = True
    extra = 0
    readonly_fields = ['play_count']


@admin.register(static_assets.StaticAsset)
class StaticAssetAdmin(AdminUserDefaultMixin, nested_admin.NestedModelAdmin):
    actions = ['process_videos']
    inlines = [ImageInline, VideoInline]
    autocomplete_fields = ['user', 'author']
    list_display = ['__str__', 'date_created', 'date_updated']
    fieldsets = (
        (
            None,
            {
                'fields': [
                    'id',
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
    list_filter = [
        'source_type',
    ]
    search_fields = [
        'source',
        'original_filename',
        'user__first_name',
        'user__last_name',
        'author__first_name',
        'author__last_name',
        'source_type',
    ]
    readonly_fields = ['original_filename', 'size_bytes', 'date_created', 'id']

    def process_videos(self, request, queryset):
        """For each asset, process all videos attached if available."""
        videos_processing_count = 0
        for a in queryset:
            a.process_video()
            videos_processing_count += 1
        if videos_processing_count == 0:
            message_bit = "No video is"
        elif videos_processing_count == 1:
            message_bit = "1 video is"
        else:
            message_bit = "%s videos are" % videos_processing_count
        self.message_user(request, "%s processing." % message_bit)

    process_videos.short_description = "Process videos for selected assets"
