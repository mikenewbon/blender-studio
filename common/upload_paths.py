"""Implements utilities related to media uploads."""
from pathlib import Path
from time import time
import hashlib
import logging
import typing
import uuid

if typing.TYPE_CHECKING:
    import static_assets.models.StaticAsset
    import films
    import training

DISALLOWED_MEDIA_PREFIXES = ['ad']
logger = logging.getLogger(__name__)


def generate_hash_from_filename(filename: str) -> typing.Optional[str]:
    """Combine filename and uuid4 and get a unique string.

    Tries to avoid prefix "ad" because it tends to trigger adblockers. Yes, for real.
    """
    attempts = 5
    while attempts:
        unique_filename = f'{uuid.uuid4()}_{filename}'
        digest = hashlib.md5(unique_filename.encode('utf-8')).hexdigest()
        attempts -= 1
        if any(digest.startswith(prefix) for prefix in DISALLOWED_MEDIA_PREFIXES):
            logger.warning(f'Had to make ({attempts}th) attempt at generate_hash_from_filename')
            continue
        return digest
    logger.error(f'Failed to generate a valid hash after {attempts} attempts')


ModelWithFile = typing.Union[
    'static_assets.models.StaticAsset',
    'films.models.Film',
    'films.models.Collection',
    'training.models.Training',
    'training.models.Video',
    'training.models.Asset',
]


def get_upload_to_hashed_path(_: ModelWithFile, filename: str) -> Path:
    """Generate a unique, hashed upload path for a source file.

    Files will be uploaded to nested directories, e.g.:
    MEDIA_ROOT/bd/bd2b5b1cd81333ed2d8db03971f91200/bd2b5b1cd81333ed2d8db03971f91200.mp4,
    where `bd` is the first two characters of the hashed filename.
    """
    extension = Path(filename).suffix
    hashed = generate_hash_from_filename(filename)
    path = Path(hashed[:2], hashed, hashed).with_suffix(extension)

    return path


def shortuid() -> str:
    """Generate a 14-characters long string ID based on time."""
    return hex(int(time() * 10000000))[2:]
