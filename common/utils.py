import hashlib
import uuid
from pathlib import Path, PosixPath

from films.models.asset import Video, File, Asset


def generate_hash_from_filename(instance_uuid: uuid.UUID, filename: str) -> str:
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = f'{instance_uuid}_{filename}'
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


def get_upload_to_hashed_path(asset: Asset, filename: str) -> PosixPath:
    """ Generate a unique, hashed upload path for an asset file.

    Every asset file gets a hashed filename. Image files are uploaded directly to MEDIA_ROOT, e.g.
    MEDIA_ROOT/bd2b5b1cd81333ed2d8db03971f91200.png.
    For each Video and File model instance, a separate folder with a unique name is created, where
    all the instance-related files (both the asset file and the preview picture) are stored;
    the folder name is the asset uuid. E.g.:
    MEDIA_ROOT/b60123d8-a0b5-44fb-ac88-1cd992e30343/886743af0e9bc9ef7636caf489d5352c.mp4
    """
    extension = Path(filename).suffix
    hashed_path = Path(generate_hash_from_filename(asset.uuid, filename))

    if isinstance(asset, (Video, File)):
        path = hashed_path.joinpath(asset.uuid).with_suffix(extension)
    else:
        path = hashed_path.with_suffix(extension)
    return path


# TODO: put it in the assets app, and write tests. Then remove this utils file!
