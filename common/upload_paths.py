import hashlib
import typing
import uuid
from pathlib import Path


def generate_hash_from_filename(filename: str) -> str:
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = f'{uuid.uuid4()}_{filename}'
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


ModelWithFile = typing.Union[
    'assets.models.StaticAsset',
    'films.models.Film',
    'films.models.Collection',
    'training.models.Training',
    'training.models.Video',
    'training.models.Asset',
]


# TODO: write tests
def get_upload_to_hashed_path(asset: ModelWithFile, filename: str) -> Path:
    """ Generate a unique, hashed upload path for a source file.

    Files will be uploaded to nested directories, e.g.:
    MEDIA_ROOT/bd/bd2b5b1cd81333ed2d8db03971f91200/bd2b5b1cd81333ed2d8db03971f91200.mp4,
    where `bd` is the first two characters of the hashed filename.
    """
    extension = Path(filename).suffix
    hashed = generate_hash_from_filename(filename)
    path = Path(hashed[:2], hashed, hashed).with_suffix(extension)

    return path
