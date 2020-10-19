from typing import Optional
import logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import FileField
from django.db.models.fields.files import FieldFile
from django.urls.base import reverse
from storages.backends.gcloud import GoogleCloudStorage

from common import mixins
from common.upload_paths import get_upload_to_hashed_path
from static_assets.models import License, StorageLocationCategoryChoices


log = logging.getLogger(__name__)


class StaticAssetFileTypeChoices(models.TextChoices):
    file = 'file', 'File'
    image = 'image', 'Image'
    video = 'video', 'Video'


class DynamicStorageFieldFile(FieldFile):
    def __init__(self, instance: models.Model, field: FileField, name: Optional[str]):
        super(DynamicStorageFieldFile, self).__init__(instance, field, name)

        assert hasattr(instance.__class__, 'storage_location'), (
            f'{self.__class__.__name__} cannot be used in {instance.__class__.__name__}, '
            f'which does not have the `storage_location` field.'
        )

        if instance.storage_location_id:  # type: ignore[attr-defined]
            # The `if` prevents an unhandled exception if one tries to save without a storage_location
            if instance.storage_location.category == StorageLocationCategoryChoices.gcs:  # type: ignore[attr-defined]
                self.storage: GoogleCloudStorage = GoogleCloudStorage()
                if instance.storage_location.bucket_name:  # type: ignore[attr-defined]
                    self.storage.bucket_name = instance.storage_location.bucket_name  # type: ignore[attr-defined]
            else:
                self.storage = FileSystemStorage()


class DynamicStorageFileField(models.FileField):
    attr_class = DynamicStorageFieldFile

    def pre_save(self, model_instance: models.Model, add: bool) -> FieldFile:
        assert hasattr(model_instance, 'storage_location'), (
            f'{self.__class__.__name__} cannot be used in {model_instance.__class__.__name__}, '
            f'which does not have the `storage_location` field.'
        )

        if model_instance.storage_location.category == StorageLocationCategoryChoices.gcs:  # type: ignore[attr-defined]
            storage = GoogleCloudStorage()
        else:
            storage = FileSystemStorage()
        self.storage = storage
        file: FieldFile = super(DynamicStorageFileField, self).pre_save(model_instance, add)
        return file


class StaticAsset(mixins.CreatedUpdatedMixin, models.Model):
    source = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)
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

    thumbnail = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)
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
    def author_name(self) -> str:
        """Get the asset's author full name.

        Usually the author of the asset will be the same as the user who uploads the asset."""
        if self.author:
            return self.author.profile.full_name
        return self.user.profile.full_name

    def clean(self):
        super().clean()
        if not self.pk and self.source:
            # Save the original filename only on asset creation.
            self.original_filename = self.source.file.name

        if self.source:
            # The `if` prevents an unhandled exception if one tries to save without a source
            self.size_bytes = self.source.size

        if self.source_type == StaticAssetFileTypeChoices.file and not self.thumbnail:
            raise ValidationError(
                f'Source preview has to be provided for `{StaticAssetFileTypeChoices.file}` source type.'
            )

    def __str__(self):
        return f'{self.source_type} {self.original_filename}'


class Video(models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    height = models.PositiveIntegerField(blank=True, null=True)
    width = models.PositiveIntegerField(blank=True, null=True)
    resolution_label = models.CharField(max_length=32, blank=True)
    duration = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    duration.description = 'Video duration in the format [DD] [[HH:]MM:]ss[.uuuuuu]'
    play_count = models.PositiveIntegerField(default=0, editable=False)

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
    source = models.FileField(upload_to=get_upload_to_hashed_path, blank=True)
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
