import random
import uuid
from contextlib import contextmanager
from io import BytesIO
from typing import Any
from unittest import mock

import PIL.Image
from django.dispatch.dispatcher import Signal


def create_test_image():
    img = PIL.Image.new('RGB', (200, 200), (73, 109, 137))
    test_image = BytesIO()
    img.save(test_image, 'png')
    test_image.seek(0)
    test_image.name = 'valid_name.png'
    return test_image


def generate_image_path() -> str:
    return f'tests/images/{uuid.uuid4()}.jpg'


def generate_file_path() -> str:
    extensions = ['jpg', 'png', 'blend', 'mp4', 'mov']
    return f'tests/assets/{uuid.uuid4()}.{random.choice(extensions)}'


@contextmanager
def catch_signal(signal: Signal, **kwargs: Any):
    """Catch django signal and return the mocked call.

    Source: https://hakibenita.com/how-to-test-django-signals-like-a-pro
    """
    handler = mock.Mock()
    signal.connect(handler, **kwargs)
    try:
        yield handler
    finally:
        signal.disconnect(handler)
