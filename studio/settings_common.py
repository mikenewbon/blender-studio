import pathlib
import sys

import meilisearch

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
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'blender_id_oauth_client',
    'debug_toolbar',
    'looper',
    'pipeline',
    'sorl.thumbnail',
    'django.contrib.humanize',
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
                'training.context_processors.enums',
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
                'training/scripts/*.js',
                'training/scripts/components/*.js',
                'comments/scripts/*.js',
                'comments/scripts/components/*.js',
                'common/scripts/*.js',
            ],
            'output_filename': 'js/studio.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'search': {
            'source_filenames': [
                'search/scripts/*.js',
            ],
            'output_filename': 'js/search.js',
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
                'common/scripts/vendor/choices.js',
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
    },
    'root': {'level': 'WARNING', 'handlers': ['console']},
}

SITE_ID = 1

# Required by Django Debug Toolbar
INTERNAL_IPS = ['127.0.0.1']


# MeiliSearch-related settings
MEILISEARCH_API_ADDRESS = 'http://127.0.0.1:7700'
if 'test' in sys.argv:
    MEILISEARCH_INDEX_UID = 'test-studio'
else:
    MEILISEARCH_INDEX_UID = 'studio'

SEARCH_CLIENT = meilisearch.Client(MEILISEARCH_API_ADDRESS)
MAIN_SEARCH_INDEX = SEARCH_CLIENT.get_index(MEILISEARCH_INDEX_UID)

DEFAULT_RANKING_RULES = [
    'typo',
    'words',
    'proximity',
    'attribute',
    'wordsPosition',
    'exactness',
]
DATE_DESC_RANKING_RULES = ['desc(date_created_ts)', *DEFAULT_RANKING_RULES]
DATE_ASC_RANKING_RULES = ['asc(date_created_ts)', *DEFAULT_RANKING_RULES]
INDEXES_FOR_SORTING = [
    (MEILISEARCH_INDEX_UID, DEFAULT_RANKING_RULES),
    (f'{MEILISEARCH_INDEX_UID}_date_desc', DATE_DESC_RANKING_RULES),
    (f'{MEILISEARCH_INDEX_UID}_date_asc', DATE_ASC_RANKING_RULES),
]

SEARCHABLE_ATTRIBUTES = [
    # Model fields/annotations that are searchable:
    #     Film: ['model', 'name', 'project', 'description', 'summary'],
    #     Asset: ['model', 'name', 'project', 'collection_name', 'description'],
    #     Training: ['model', 'name', 'project', 'description', 'summary'],
    #     Section: ['model', 'name', 'project', 'chapter_name', 'description'],
    #     Post: ['model', 'name', 'project', 'topic', 'description', 'content']
    # In the order of relevance:
    'model',
    'name',
    'project',
    'topic',
    'collection_name',
    'chapter_name',
    'description',
    'summary',
    'content',
]
FACETING_ATTRIBUTES = ['model', 'project', 'license', 'media_type']
