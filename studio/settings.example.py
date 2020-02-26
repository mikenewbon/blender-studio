import os

# noinspection PyUnresolvedReferences
from typing import List

from studio.settings_common import *

# Enable to use OAuth without https during local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SECRET_KEY = '7ijgr7*_l=x^f0!((j!*sdfsdfsdf*xfbf3vcz0=#!5aai85$h3ck6l9m3c'
DEBUG = True
ALLOWED_HOSTS: List[str] = ['training.local']

BLENDER_ID = {
    # MUST end in a slash:
    "BASE_URL": "http://id.local:8000/",
    "OAUTH_CLIENT": "dsfsd",
    "OAUTH_SECRET": "sdfsdfsd",
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
