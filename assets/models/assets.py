from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.fields.files import FieldFile
from django.core.files.storage import FileSystemStorage
from storages.backends.gcloud import GoogleCloudStorage

from assets.models import License, StorageBackend, StorageBackendCategoryChoices
from common import mixins
from common.upload_paths import get_upload_to_hashed_path


class AssetFileTypeChoices(models.TextChoices):
    file = 'file', 'File'
    image = 'image', 'Image'
    video = 'video', 'Video'


class DynamicStorageFieldFile(FieldFile):
    def __init__(self, instance: "StaticAsset", field, name):
        super(DynamicStorageFieldFile, self).__init__(instance, field, name)
        if instance.storage_backend.category == StorageBackendCategoryChoices.gcs.value:
            self.storage: GoogleCloudStorage = GoogleCloudStorage()
            if instance.storage_backend.bucket_name:
                self.storage.bucket_name = instance.storage_backend.bucket_name
        else:
            self.storage = FileSystemStorage()


class DynamicStorageFileField(models.FileField):
    attr_class = DynamicStorageFieldFile

    def pre_save(self, model_instance: "StaticAsset", add):
        if model_instance.storage_backend.category == StorageBackendCategoryChoices.gcs.value:
            storage = GoogleCloudStorage()
        else:
            storage = FileSystemStorage()
        self.storage = storage
        file = super(DynamicStorageFileField, self).pre_save(model_instance, add)
        return file


class StaticAsset(mixins.CreatedUpdatedMixin, models.Model):
    source = DynamicStorageFileField(upload_to=get_upload_to_hashed_path)
    source_type = models.CharField(choices=AssetFileTypeChoices.choices, max_length=5)
    # TODO(Natalia): source type validation
    original_filename = models.CharField(max_length=128, editable=False)
    size_bytes = models.BigIntegerField(editable=False)

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_assets')
    user.description = "The user who uploaded the asset."
    author = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.PROTECT, related_name='authored_assets'
    )
    author.description = "The actual author of the artwork/learning materials."
    license = models.ForeignKey(
        License, null=True, on_delete=models.SET_NULL, related_name='assets'
    )
    storage_backend = models.ForeignKey(
        StorageBackend, on_delete=models.CASCADE, related_name='assets'
    )

    source_preview = DynamicStorageFileField(upload_to=get_upload_to_hashed_path, blank=True)
    source_preview.description = (
        "Asset preview is auto-generated for images and videos. Required for other files."
    )

    # TODO(Natalia): generate preview if source_preview not uploaded.
    @property
    def preview(self):
        if self.source_preview:
            return self.source_preview
        if self.source_type == AssetFileTypeChoices.image:
            return self.source
        # TODO(Natalia): Update this once we have auto-generated previews.

    @property
    def author_name(self) -> str:
        """ Get the asset's author full name.

        Usually the author of the asset will be the same as the user who uploads the asset. """
        if self.author:
            return self.author.get_full_name()
        return self.user.get_full_name()

    def clean(self):
        super().clean()
        self.original_filename = self.source.file.name
        self.size_bytes = self.source.size

        if self.source_type == AssetFileTypeChoices.file and not self.source_preview:
            raise ValidationError(
                f'Source preview has to be provided for `{AssetFileTypeChoices.file}` source type.'
            )

    def __str__(self):
        return f'{self.source_type} {self.original_filename}'


class Video(mixins.CreatedUpdatedMixin, models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)
    duration_seconds = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    play_count = models.PositiveIntegerField(default=0, editable=False)

    def __str__(self) -> str:
        return f'{self._meta.model_name} {self.static_asset.original_filename}'


class Image(mixins.CreatedUpdatedMixin, models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f'{self._meta.model_name} {self.static_asset.original_filename}'


# TODO(Natalia): Handle deleting all these files when a model instance is deleted from the db?
