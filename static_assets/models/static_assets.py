import datetime
import logging
import mimetypes

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.urls.base import reverse
from sorl.thumbnail import get_thumbnail

from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from static_assets.models import License
from static_assets.tasks import create_video_processing_job
import common.storage


log = logging.getLogger(__name__)


class StaticAssetFileTypeChoices(models.TextChoices):
    file = 'file', 'File'
    image = 'image', 'Image'
    video = 'video', 'Video'


class DynamicStorageFileField(models.FileField):
    pass  # kept because migrations refer to this field


class StaticAsset(mixins.CreatedUpdatedMixin, mixins.StaticThumbnailURLMixin, models.Model):
    class Meta:
        ordering = ['-date_created']

    source = models.FileField(
        upload_to=get_upload_to_hashed_path,
        storage=common.storage.S3Boto3CustomStorage(),
        blank=True,
        max_length=256,
    )
    source_type = models.CharField(choices=StaticAssetFileTypeChoices.choices, max_length=5)
    # TODO(Natalia): source type validation
    original_filename = models.CharField(max_length=128, editable=False)
    size_bytes = models.BigIntegerField(editable=False)

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='uploaded_assets', verbose_name='created by'
    )
    user.description = 'The user who created the static asset.'
    author = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='authored_assets',
        verbose_name='author (optional)',
        help_text='The actual author of the artwork/learning materials',
    )
    author.description = 'The actual author of the artwork/learning materials.'
    license = models.ForeignKey(
        License, null=True, on_delete=models.SET_NULL, related_name='static_assets'
    )

    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path, blank=True, max_length=256)
    thumbnail.description = (
        "Asset thumbnail is auto-generated for images and videos. Required for other files."
    )

    # Reference to legacy Blender Cloud file
    slug = models.SlugField(blank=True)

    content_type = models.CharField(max_length=256, blank=True)

    # TODO(Natalia): generate preview if thumbnail not uploaded.
    @property
    def preview(self):
        if self.thumbnail:
            return self.thumbnail
        if self.source_type == StaticAssetFileTypeChoices.image:
            return self.source
        # TODO(Natalia): Update this once we have auto-generated thumbnails.

    @property
    def thumbnail_m_url(self) -> str:
        """Return a static URL to a medium-sizes thumbnail."""
        # TODO(anna): use StaticThumbnailURLMixin once thumbnails are generated
        preview = self.preview
        if not preview:
            return ''
        return get_thumbnail(
            preview, settings.THUMBNAIL_SIZE_M, crop=settings.THUMBNAIL_CROP_MODE
        ).url

    @property
    def thumbnail_s_url(self) -> str:
        """Return a static URL to a small thumbnail."""
        # TODO(anna): use StaticThumbnailURLMixin once thumbnails are generated
        preview = self.preview
        if not preview:
            return ''
        return get_thumbnail(
            preview, settings.THUMBNAIL_SIZE_S, crop=settings.THUMBNAIL_CROP_MODE
        ).url

    @property
    def author_name(self) -> str:
        """Get the asset's author full name.

        Usually the author of the asset will be the same as the user who uploads the asset.
        """
        if self.author:
            return self.author.profile.full_name
        return self.user.profile.full_name

    @property
    def author_image_url(self) -> str:
        """Get the asset's author's image.

        Usually the author of the asset will be the same as the user who uploads the asset.
        """
        if self.author:
            return self.author.profile.image_url
        return self.user.profile.image_url

    def process_video(self):
        """Create video processing task if asset has correct type."""
        if self.source_type != StaticAssetFileTypeChoices.video:
            return
        if not self.source:
            return
        # Create a background job, using only hashable arguments
        create_video_processing_job(self.id)

    def clean(self):
        super().clean()
        if not self.pk and self.source:
            # Save the original filename only on asset creation.
            self.original_filename = self.source.file.name

        if self.source:
            # The `if` prevents an unhandled exception if one tries to save without a source
            self.size_bytes = self.source.size
            if not self.source_type:
                content_type, _ = mimetypes.guess_type(self.original_filename)
                if 'image' in content_type:
                    self.source_type = StaticAssetFileTypeChoices.image
                elif 'video' in content_type:
                    self.source_type = StaticAssetFileTypeChoices.video

        if self.source_type == StaticAssetFileTypeChoices.file and not self.thumbnail:
            raise ValidationError(
                f'Source preview has to be provided for `{self.source_type}` source type.'
            )

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if not created:
            return
        # Create related tables for video or image
        if self.source_type == 'video':
            Video.objects.create(static_asset=self, duration=datetime.timedelta(seconds=0))
            self.process_video()
        elif self.source_type == 'image':
            Image.objects.create(static_asset=self)
            # TODO(fsiddi) Background job to update the image info

    def __str__(self):
        return f'({self.id}) {self.original_filename}'


class Video(models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    height = models.PositiveIntegerField(blank=True, null=True)
    width = models.PositiveIntegerField(blank=True, null=True)
    resolution_label = models.CharField(max_length=32, blank=True)
    duration = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    duration.description = 'Video duration in the format [DD] [[HH:]MM:]ss[.uuuuuu]'
    play_count = models.PositiveIntegerField(default=0, editable=False)

    @property
    def duration_label(self):
        """A duration label that adaptively displays time.

        For example: 0:02, 1:02, 10:02, 1:20:01.
        """
        total_seconds = int(self.duration.total_seconds())
        remaining_hours = total_seconds % 86400
        remaining_minutes = remaining_hours % 3600
        hours = remaining_hours // 3600
        minutes = remaining_minutes // 60
        seconds = remaining_minutes % 60

        # Show hours only if present
        hours_str = f'{hours}:' if hours else ''

        # Show minutes with zero padding only if hours are present
        if minutes and hours:
            minutes_str = f'{minutes:02d}:'
        elif minutes:
            minutes_str = f'{minutes}:'
        # Show zero minutes when no minutes are present (0:12)
        else:
            minutes_str = '0:'
        # Always pad seconds display
        seconds_str = f'{seconds:02d}'
        return f'{hours_str}{minutes_str}{seconds_str}'

    @property
    def default_variation_url(self):
        default_variation: VideoVariation = self.variations.first()
        # TODO(fsiddi) ensure that default_variation.source is never None
        if not default_variation or not default_variation.source:
            log.warning('Variation for video %i not found' % self.pk)
            return self.static_asset.source.url
        return default_variation.source.url

    @property
    def progress_url(self) -> str:
        return reverse('video-progress', kwargs={'video_pk': self.pk})

    def __str__(self) -> str:
        return f'{self._meta.model_name} {self.static_asset.original_filename}'


class VideoVariation(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='variations')
    height = models.PositiveIntegerField(blank=True, null=True)
    width = models.PositiveIntegerField(blank=True, null=True)
    resolution_label = models.CharField(max_length=32, blank=True)
    source = models.FileField(upload_to=get_upload_to_hashed_path, blank=True, max_length=256)
    size_bytes = models.BigIntegerField(editable=False)
    content_type = models.CharField(max_length=256, blank=True)

    def __str__(self) -> str:
        return f"Video variation for {self.video.static_asset.original_filename}"


class Image(models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    height = models.PositiveIntegerField(blank=True, null=True)
    width = models.PositiveIntegerField(blank=True, null=True)
    resolution_label = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f'{self._meta.model_name} {self.static_asset.original_filename}'


# TODO(Natalia): Handle deleting all these files when a model instance is deleted from the db?
