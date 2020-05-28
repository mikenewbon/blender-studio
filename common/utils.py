import hashlib
import uuid
from pathlib import Path

from films.models.asset import Video


# TODO: adapt these functions
def generate_hash_from_filename(filename):
    """Combine filename and uuid4 and get a unique string."""
    unique_filename = str(uuid.uuid4()) + filename
    return hashlib.md5(unique_filename.encode('utf-8')).hexdigest()


def get_upload_to_hashed_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/<bd>/<bd2b5b1cd81333ed2d8db03971f91200>
    extension = Path(filename).suffix
    hashed = generate_hash_from_filename(filename)

    path = Path(hashed[:2], hashed[2:4])
    if isinstance(instance, Video):
        path = path.joinpath(hashed, hashed).with_suffix(extension)
    else:
        path = path.joinpath(hashed).with_suffix(extension)
    return path
