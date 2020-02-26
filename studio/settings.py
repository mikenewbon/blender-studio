import os

# noinspection PyUnresolvedReferences
from typing import List

from studio.settings_common import *

# Enable to use OAuth without https during local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SECRET_KEY = '7ijgr7*_l=x^f0!((j!*sdfsdfsdf*xfbf3vcz0=#!5aai85$h3ck6l9m3c'
DEBUG = True
ALLOWED_HOSTS: List[str] = ['studio.local', '10.161.30.53']

BLENDER_ID = {
    # MUST end in a slash:
    "BASE_URL": "http://id.local:8000/",
    "OAUTH_CLIENT": "CEnHQmv2nn4fjDlzQMVgi6DapThBEJW6Tsy6ARjS",
    "OAUTH_SECRET": "VZZncrIBlttw9Mng7SfOoBKYD4YoOnZTOqUw0IZIxfKiKIZ3MNbsbZlcph1OnaqhgPeVEkIXDzatX5H8scnZ1vq0739VwzLC7ke9ucHU8s6G5ZoKm8a7BSeTndvMLV2I",
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'studio',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
