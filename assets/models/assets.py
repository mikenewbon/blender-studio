import hashlib
import uuid
from pathlib import Path

from django.contrib.auth.models import User
from django.db import models

from assets.models import License, StorageBackend
from common import mixins


# TODO: write tests
def generate_hash_from_filename(filename: str) -> str:
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = f'{uuid.uuid4()}_{filename}'
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


def get_upload_to_hashed_path(asset: 'StaticAsset', filename: str) -> Path:
    """ Generate a unique, hashed upload path for an asset source file.

    Videos and files will be uploaded to nested directories:
    MEDIA_ROOT/<bd>/<bd2b5b1cd81333ed2d8db03971f91200>/.
    Images - to MEDIA_ROOT/<bd>/
    """
    # TODO: think of a better parameter name? it's not an Asset instance anymore
    extension = Path(filename).suffix
    hashed = generate_hash_from_filename(filename)
    path = Path(hashed[:2], hashed)

    if asset.source_type == AssetFileTypeChoices.image:
        path = path.with_suffix(extension)
    else:
        path = path.joinpath(hashed).with_suffix(extension)
    return path


class AssetFileTypeChoices(models.TextChoices):
    file = 'file', 'File'
    image = 'image', 'Image'
    video = 'video', 'Video'


class StaticAsset(mixins.CreatedUpdatedMixin, models.Model):
    source = models.FileField(upload_to=get_upload_to_hashed_path)
    source_type = models.CharField(choices=AssetFileTypeChoices.choices, max_length=5)
    # TODO: source type validation
    original_filename = models.CharField(max_length=128)
    size_bytes = models.IntegerField()

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_assets')
    user.description = "The user who uploaded the asset."
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='authored_assets')
    author.description = "The actual author of the artwork/learning materials."
    license = models.ForeignKey(
        License, null=True, on_delete=models.SET_NULL, related_name='assets'
    )
    storage_backend = models.ForeignKey(
        StorageBackend, on_delete=models.CASCADE, related_name='assets'
    )

    source_preview = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True)
    source_preview.description = "Optional asset preview. If not provided, it will be generated."
    # TODO: generate preview if not uploaded
    # TODO: files should always have the preview uploaded - add validation?
    # @property # or a field?
    # def preview(self):
    #     return self.source_preview or ...


class Video(mixins.CreatedUpdatedMixin, models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)
    duration_seconds = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    play_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return (
            f"{self._meta.model_name} {self.static_asset.original_filename} in "
            f"{self.static_asset.storage_backend.project}"
        )


class Image(mixins.CreatedUpdatedMixin, models.Model):
    static_asset = models.OneToOneField(StaticAsset, on_delete=models.CASCADE)
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return (
            f"{self._meta.model_name} {self.static_asset.original_filename} in "
            f"{self.static_asset.storage_backend.project}"
        )


# TODO: Handle deleting all these files when a model instance is deleted from the db?
# TODO: size could be retrieved: source.size (cached property of django.core.files.base.File)
