import hashlib
import uuid
from pathlib import Path
from typing import Union

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify

from assets.models.licenses import License
from common import mixins
from films.models.collections import Collection
from films.models.films import Film


# TODO: write tests
def generate_hash_from_filename(filename: str) -> str:
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = f'{uuid.uuid4()}_{filename}'
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


def get_upload_to_hashed_path(asset: Union['Video', 'Image', 'File'], filename: str) -> Path:
    """ Generate a unique, hashed upload path for an asset source file.

    Videos and files will be uploaded to nested directories:
    MEDIA_ROOT/films/<bd>/<bd2b5b1cd81333ed2d8db03971f91200>/.
    Images - to MEDIA_ROOT/films/<bd>/
    """
    # TODO: think of a better parameter name? it's not an Asset instance anymore
    extension = Path(filename).suffix
    hashed = generate_hash_from_filename(filename)
    path = Path('films', hashed[:2])

    if isinstance(asset, (Video, File)):
        path = path.joinpath(hashed, hashed).with_suffix(extension)
    else:
        path = path.joinpath(hashed).with_suffix(extension)
    return path


class AssetCategory(models.TextChoices):
    artwork = 'artwork', 'Artwork'
    production_file = 'production_file', 'Production File'
    production_lesson = 'production_lesson', 'Production Lesson'


class Asset(mixins.CreatedUpdatedMixin, models.Model):
    """ This represents the leaf of the tree of film-related resources.

    An asset can be of one of the three types: image, video, or file.
    """

    class Meta:
        constraints = []  # TODO: only one related file (img, video, file)

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
    author.description = "The actual author of the artwork/learning materials."
    view_count = models.PositiveIntegerField(default=0)

    visibility = models.BooleanField(default=False)

    @property
    def picture_16_9(self):
        # TODO: This sends a db query for each attribute check. Use `select_related` in view?
        if hasattr(self, 'image'):
            return self.image.picture_16_9
        if hasattr(self, 'video'):
            return self.video.picture_16_9
        if hasattr(self, 'file'):
            return self.file.picture_16_9

    def clean(self) -> None:
        super().clean()
        if not self.slug:
            self.slug = slugify(self.name)

    def __str__(self) -> str:
        return self.name


class Video(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    source = models.FileField(upload_to=get_upload_to_hashed_path)
    original_filename = models.CharField(max_length=128)
    size_bytes = models.IntegerField()
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)
    duration_seconds = models.DurationField(help_text='[DD] [[HH:]MM:]ss[.uuuuuu]')
    picture_16_9 = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True)
    # TODO: generate picture_16_9 if not uploaded

    play_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.source.path} in {self.asset.name}"


class Image(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    source = models.ImageField(upload_to=get_upload_to_hashed_path)
    original_filename = models.CharField(max_length=128)
    size_bytes = models.IntegerField()
    resolution = models.CharField(max_length=32, blank=True)
    resolution_text = models.CharField(max_length=32, blank=True)
    picture_16_9 = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True)

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.source.path} in {self.asset.name}"


class File(mixins.CreatedUpdatedMixin, models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    source = models.FileField(upload_to=get_upload_to_hashed_path)
    original_filename = models.CharField(max_length=128)
    size_bytes = models.IntegerField()
    picture_16_9 = models.ImageField(upload_to=get_upload_to_hashed_path, blank=True)
    # TODO: generate picture_16_9 if not uploaded

    def __str__(self) -> str:
        return f"{self._meta.model_name} {self.source.path} in {self.asset.name}"


# TODO: Handle deleting all these files when a model instance is deleted from the db?
# TODO: size could be retrieved: source.size (cached property of django.core.files.base.File)
