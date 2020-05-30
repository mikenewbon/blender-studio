import hashlib
import uuid
from pathlib import Path

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify

from assets.models.licenses import License
from common import mixins
from films.models.collections import Collection
from films.models.films import Film


# TODO: write tests
def generate_hash_from_filename(instance_uuid: uuid.UUID, filename: str) -> str:
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = f'{instance_uuid}_{filename}'
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


def get_upload_to_hashed_path(asset: 'Asset', filename: str) -> Path:
    """ Generate a unique, hashed upload path for an asset file.

    Every asset file gets a hashed filename. Image files are uploaded directly to MEDIA_ROOT, e.g.
    MEDIA_ROOT/bd2b5b1cd81333ed2d8db03971f91200.png.
    For each Video and File model instance, a separate folder with a unique name is created, where
    all the instance-related files (both the asset file and the preview picture) are stored;
    the folder name is the asset uuid. E.g.:
    MEDIA_ROOT/b60123d8-a0b5-44fb-ac88-1cd992e30343/886743af0e9bc9ef7636caf489d5352c.mp4
    """
    extension = Path(filename).suffix
    hashed_path = Path(generate_hash_from_filename(asset.asset.uuid, filename))

    if isinstance(asset, (Video, File)):
        dir_path = Path(str(asset.asset.uuid))
        path = dir_path.joinpath(hashed_path).with_suffix(extension)
    else:
        path = hashed_path.with_suffix(extension)
    return path


class AssetCategory(models.TextChoices):
    artwork = 'artwork', 'Artwork'
    production_file = 'production_file', 'Production File'
    production_lesson = 'production_lesson', 'Production Lesson'


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    """ This represents the leaf of the tree of film-related resources. """

    class Meta:
        constraints = []  # TODO: only one related file (img, video, file)

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    film = models.ForeignKey(Film, on_delete=models.CASCADE, related_name='assets')
    collection = models.ForeignKey(
        Collection, blank=True, null=True, on_delete=models.SET_NULL, related_name='assets'
    )
    order = models.IntegerField()

    name = models.CharField(max_length=512)
    slug = models.SlugField(blank=True)
    text = models.TextField()
    license = models.ForeignKey(
        License, null=True, on_delete=models.SET_NULL, related_name='assets'
    )

    category = models.CharField(choices=AssetCategory.choices, max_length=17, db_index=True)

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_assets')
    user.description = "The user who uploaded the asset."
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='authored_assets')
    author.description = "The actual author of the asset."
    view_count = models.PositiveIntegerField(default=0)

    visibility = models.BooleanField(default=False)

    @property
    def picture_16_9(self):
        # TODO: get appropriate picture from the related img/video/file
        pass

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return self.name


class Video(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_upload_to_hashed_path)
    size_bytes = models.IntegerField()
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)
    duration_seconds = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    preview = models.ImageField(upload_to=get_upload_to_hashed_path)

    play_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.file.path} in {self.asset.name}"


class Image(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    file = models.ImageField(upload_to=get_upload_to_hashed_path)
    size_bytes = models.IntegerField()
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.file.path} in {self.asset.name}"


class File(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_upload_to_hashed_path)
    size_bytes = models.IntegerField()
    preview = models.ImageField(upload_to=get_upload_to_hashed_path)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.file.path} in {self.asset.name}"


# TODO: Handle deleting all these files when a model instance is deleted from the db?
# TODO: size could be retrieved: file.size (cached property of django.core.files.base.File)
