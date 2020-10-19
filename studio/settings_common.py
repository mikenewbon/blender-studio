# noqa: D100
from datetime import timedelta
import os  # noqa: F401
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

ADMIN_SITE_HEADER = 'Blender Studio Admin'
ADMIN_SITE_TITLE = 'Blender Studio'

# Application definition

INSTALLED_APPS = [
    'blog',
    'comments',
    'common',
    'films',
    'search',
    'static_assets',
    'subscriptions',
    'training',
    'profiles',
    'cloud_import',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'blender_id_oauth_client',
    'blendercloud',
    'debug_toolbar',
    'looper',
    'pipeline',
    'sorl.thumbnail',
    'taggit',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'blendercloud.middleware.SessionMiddleware',
]

ROOT_URLCONF = 'studio.urls'

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATIC_ROOT = BASE_DIR / 'public/static'
MEDIA_ROOT = BASE_DIR / 'public/media'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            str(BASE_DIR / 'comments/templates'),
            str(BASE_DIR / 'common/templates'),
            str(BASE_DIR / 'films/templates'),
            str(BASE_DIR / 'search/templates'),
            str(BASE_DIR / 'training/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'common.context_processors.search_client_config',
                'training.context_processors.enums',
                # TODO(anna) when Profile model is added, this should become a prop on it instead.
                'training.context_processors.favorited',
                'profiles.context_processors.user_dict',
            ]
        },
    },
]

WSGI_APPLICATION = 'studio.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Blender ID login with Blender ID OAuth client

LOGIN_URL = '/oauth/login'
LOGOUT_URL = '/oauth/logout'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

PIPELINE = {
    'JS_COMPRESSOR': 'pipeline.compressors.jsmin.JSMinCompressor',
    'CSS_COMPRESSOR': 'pipeline.compressors.NoopCompressor',
    'JAVASCRIPT': {
        'studio': {
            'source_filenames': [
                'comments/scripts/*.js',
                'comments/scripts/components/*.js',
                'common/scripts/*.js',
            ],
            'output_filename': 'js/studio.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'training': {
            'source_filenames': [
                'training/scripts/section.js',
                'training/scripts/components/card_training.js',
                'training/scripts/components/video_player.js',
            ],
            'output_filename': 'js/training_search.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'search': {
            'source_filenames': ['search/scripts/*.js',],
            'output_filename': 'js/search.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'training_search': {
            'source_filenames': ['training/scripts/training_search.js',],
            'output_filename': 'js/training_search.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'vendor': {
            'source_filenames': [
                'common/scripts/vendor/popper.min.js',
                'common/scripts/vendor/jquery-3.5.1.js',
                'common/scripts/vendor/bootstrap.js',
                'common/scripts/vendor/plyr.polyfilled.js',
                'common/scripts/vendor/js.cookie.js',
                'common/scripts/vendor/masonry.pkgd.js',
                'common/scripts/vendor/imagesloaded.pkgd.js',
            ],
            'output_filename': 'js/vendor.js',
            'extra_context': {'async': False, 'defer': False},
        },
    },
    'STYLESHEETS': {
        'studio': {
            'source_filenames': ('common/styles/studio/studio.scss',),
            'output_filename': 'css/studio.css',
            'extra_context': {'media': 'screen'},
        },
    },
    'COMPILERS': ('libsasscompiler.LibSassCompiler',),
}

STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(asctime)-15s %(levelname)8s %(name)s %(message)s'},
        'verbose': {
            'format': '%(asctime)-15s %(levelname)8s %(name)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',  # Set to 'verbose' in production
            'stream': 'ext://sys.stderr',
        },
    },
    'loggers': {
        'asyncio': {'level': 'WARNING'},
        'django': {'level': 'WARNING'},
        'urllib3': {'level': 'WARNING'},
        'search': {'level': 'DEBUG'},
        'blendercloud': {'level': 'DEBUG'},
    },
    'root': {'level': 'WARNING', 'handlers': ['console']},
}

SITE_ID = 1

# Required by Django Debug Toolbar
INTERNAL_IPS = ['127.0.0.1']


# MeiliSearch-related settings. See also settings.py.
if 'test' in sys.argv:
    MEILISEARCH_INDEX_UID = 'test_studio'
    TRAINING_INDEX_UID = 'test_training'
else:
    MEILISEARCH_INDEX_UID = 'studio'
    TRAINING_INDEX_UID = 'training'

DEFAULT_RANKING_RULES = [
    'typo',
    'words',
    'proximity',
    'attribute',
    'wordsPosition',
    'exactness',
]
DATE_DESC_RANKING_RULES = ['desc(timestamp)', *DEFAULT_RANKING_RULES]
DATE_ASC_RANKING_RULES = ['asc(timestamp)', *DEFAULT_RANKING_RULES]
MAIN_SEARCH = {
    'SEARCHABLE_ATTRIBUTES': [
        'model',
        'name',
        'project',
        'tags',
        'secondary_tags',
        'topic',
        'collection_name',
        'chapter_name',
        'description',
        'summary',
        'content',
    ],
    'FACETING_ATTRIBUTES': ['model', 'project', 'license', 'media_type', 'free'],
    'RANKING_RULES': {
        MEILISEARCH_INDEX_UID: DEFAULT_RANKING_RULES,
        f'{MEILISEARCH_INDEX_UID}_date_desc': DATE_DESC_RANKING_RULES,
        f'{MEILISEARCH_INDEX_UID}_date_asc': DATE_ASC_RANKING_RULES,
    },
}
TRAINING_SEARCH = {
    'SEARCHABLE_ATTRIBUTES': [
        'model',
        'name',
        'project',
        'tags',
        'secondary_tags',
        'chapter_name',
        'description',
        'summary',
    ],
    'FACETING_ATTRIBUTES': ['type', 'difficulty'],
    'RANKING_RULES': {
        TRAINING_INDEX_UID: DEFAULT_RANKING_RULES,
        f'{TRAINING_INDEX_UID}_date_desc': DATE_DESC_RANKING_RULES,
        f'{TRAINING_INDEX_UID}_date_asc': DATE_ASC_RANKING_RULES,
    },
}


TAGGIT_CASE_INSENSITIVE = True

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
PUBLIC_FILE_STORAGE = 'common.storage.S3PublicStorage'
# Do not set "public-read" ACL on bucket items
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_S3_REGION_NAME = 'eu-central-1'
AWS_STORAGE_BUCKET_NAME = 'blender-studio'
AWS_S3_CUSTOM_DOMAIN = 'ddz4ak4pa3d19.cloudfront.net'

THUMBNAIL_STORAGE = PUBLIC_FILE_STORAGE
THUMBNAIL_CROP_MODE = 'center'
THUMBNAIL_SIZE_S = '400x225'
THUMBNAIL_SIZE_M = '1280x720'

BLENDER_CLOUD_SESSION_COOKIE_NAME = 'session'
# Caveat emptor:
# BLENDER_CLOUD_SESSION_LIFETIME should be **at least as long** as Blender Cloud's session lifetime,
# otherwise Blender Studio will consider a session invalid **before** Blender Cloud does,
# meaning that people will appear to be logged out on Blender Studio pages,
# even if they are logged in in Blender Cloud.
# Assumes a default Flask's value for the session lifetime.
# See https://flask.palletsprojects.com/en/1.0.x/config/#PERMANENT_SESSION_LIFETIME
BLENDER_CLOUD_SESSION_LIFETIME = timedelta(days=31)
BLENDER_CLOUD_AUTH_ENABLED = False
BLENDER_CLOUD_SECRET_KEY = 'CHANGE_ME'
# If set, only use Blender Cloud session cookie for this specific domain
BLENDER_CLOUD_DOMAIN = None
