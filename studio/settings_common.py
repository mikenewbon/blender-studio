# noqa: D100
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import os  # noqa: F401
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

ADMIN_SITE_HEADER = 'Blender Studio Admin'
ADMIN_SITE_TITLE = 'Blender Studio'

# Application definition

INSTALLED_APPS = [
    'django.contrib.redirects',
    'django.contrib.flatpages',
    'django_jsonfield_backport',
    'emails',
    'blog',
    'comments',
    'common',
    'films',
    'search',
    'static_assets',
    'subscriptions',
    'training',
    'cloud_import',
    'stats',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'waffle',
    'blender_id_oauth_client',
    'blendercloud',
    'profiles',
    'debug_toolbar',
    'looper',
    'pipeline',
    'sorl.thumbnail',
    'taggit',
    'actstream',
    'background_task',
    'users',
    'loginas',
    'nested_admin',
]

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'blendercloud.middleware.SessionMiddleware',
    'subscriptions.middleware.SetCurrencyMiddleware',
    'waffle.middleware.WaffleMiddleware',
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
                'common.context_processors.settings_analytics_id',
                'common.context_processors.extra_context',
                'training.context_processors.enums',
                # TODO(anna) when Profile model is added, this should become a prop on it instead.
                'training.context_processors.favorited',
                'users.context_processors.user_dict',
                'looper.context_processors.preferred_currency',
                'loginas.context_processors.impersonated_session_status',
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

TIME_ZONE = 'Europe/Amsterdam'

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
                'training/scripts/training.js',
                'training/scripts/components/card_training.js',
            ],
            'output_filename': 'js/training.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'search': {
            'source_filenames': ['search/scripts/*.js'],
            'output_filename': 'js/search.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'training_search': {
            'source_filenames': ['training/scripts/training_search.js'],
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
                'common/scripts/vendor/imagesloaded.pkgd.js',
                'common/scripts/vendor/confetti.browser.min.js',
            ],
            'output_filename': 'js/vendor.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'vendor_instantsearch': {
            'source_filenames': [
                'common/scripts/vendor/instant-meilisearch.umd.min.js',
                'common/scripts/vendor/instantsearch.js',
            ],
            'output_filename': 'js/vendor_instantsearch.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'vendor_chartjs': {
            'source_filenames': ['common/scripts/vendor/chart.bundle.min.js'],
            'output_filename': 'js/vendor_chartjs.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'vendor_masonry': {
            'source_filenames': ['common/scripts/vendor/masonry.pkgd.js'],
            'output_filename': 'js/vendor_masonry.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'looper': {
            'source_filenames': [
                'looper/scripts/*.js',
            ],
            'output_filename': 'js/looper.js',
            'extra_context': {'async': False, 'defer': False},
        },
        'subscriptions': {
            'source_filenames': [
                'common/scripts/ajax.js',
                'subscriptions/scripts/*.js',
            ],
            'output_filename': 'js/subscriptions.js',
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
    'DISABLE_WRAPPER': True,
}

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

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
        'static_assets': {'level': 'DEBUG'},
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
        'author_name',
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
        'author_name',
    ],
    'FACETING_ATTRIBUTES': ['type', 'difficulty'],
    'RANKING_RULES': {
        TRAINING_INDEX_UID: DEFAULT_RANKING_RULES,
        f'{TRAINING_INDEX_UID}_date_desc': DATE_DESC_RANKING_RULES,
        f'{TRAINING_INDEX_UID}_date_asc': DATE_ASC_RANKING_RULES,
    },
}


TAGGIT_CASE_INSENSITIVE = True

GOOGLE_ANALYTICS_TRACKING_ID = ''
GOOGLE_RECAPTCHA_SITE_KEY = ''
GOOGLE_RECAPTCHA_SECRET_KEY = ''

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
PUBLIC_FILE_STORAGE = 'common.storage.S3PublicStorage'
# Do not set "public-read" ACL on bucket items
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_S3_REGION_NAME = 'eu-central-1'
AWS_STORAGE_BUCKET_NAME = 'blender-studio'
AWS_S3_CUSTOM_DOMAIN = 'ddz4ak4pa3d19.cloudfront.net'
# Used for temporary storage when processing videos (and in the future
# when performing direct-to-s3 uploads). Once the upload is completed
# we take care of moving the file to AWS_STORAGE_BUCKET_NAME through a
# background task.
AWS_UPLOADS_BUCKET_NAME = 'blender-studio-uploads'

THUMBNAIL_STORAGE = PUBLIC_FILE_STORAGE
THUMBNAIL_CROP_MODE = 'center'
THUMBNAIL_SIZE_S = '400x225'
THUMBNAIL_SIZE_M = '1280x720'

BLENDER_CLOUD_SESSION_COOKIE_NAME = 'session'
BLENDER_CLOUD_REMEMBER_COOKIE_NAME = 'remember_token'
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
CSRF_COOKIE_NAME = 'bstudiocsrftoken'

ACTSTREAM_SETTINGS = {
    'MANAGER': 'users.managers.CustomStreamManager',
    'FETCH_RELATIONS': True,
}
NEWSLETTER_LIST = None
NEWSLETTER_NONSUBSCRIBER_LIST = None
NEWSLETTER_SUBSCRIBER_LIST = None
MAILGUN_SENDER_DOMAIN = 'sandboxf44696c342d9425abae785deb255717e.mailgun.org'

ADMIN_MAIL = 'cloudsupport@blender.org'
STORE_PRODUCT_URL = 'https://store.blender.org/product/membership/'
STORE_MANAGE_URL = 'https://store.blender.org/my-account/subscriptions/'

# Collection of automatically renewing subscriptions will be attempted this
# many times before giving up and setting the subscription status to 'on-hold'.
#
# This value is only used when automatic renewal fails, so setting it < 1 will
# be treated the same as 1 (one attempt is made, and failure is immediate, no
# retries).
LOOPER_CLOCK_MAX_AUTO_ATTEMPTS = 3

# Only retry collection of automatic renewals this long after the last failure.
# This separates the frequency of retrials from the frequency of the clock.
LOOPER_ORDER_RETRY_AFTER = relativedelta(days=2)

# This user is required for logging things in the admin history
# (those log entries always need to have a non-NULL user ID).
LOOPER_SYSTEM_USER_ID = 1

# Convertion rates from the given rate to euros.
# This allows us to express the foreign currency in €.
LOOPER_CONVERTION_RATES_FROM_EURO = {
    'EUR': 1.0,
    'USD': 1.15,
}
LOOPER_SUBSCRIPTION_CREATION_WARNING_THRESHOLD = relativedelta(days=1)
LOOPER_ORDER_RECEIPT_PDF_URL = 'subscriptions:receipt-pdf'
LOOPER_PAY_EXISTING_ORDER_URL = 'subscriptions:pay-existing-order'
LOOPER_MANAGER_MAIL = 'CHANGE_ME'

# By default, dump emails to the console instead of trying to actually send them.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allow missing feature flags and switches to be created
WAFFLE_CREATE_MISSING_FLAGS = True
WAFFLE_CREATE_MISSING_SWITCHES = True

TESTS_IN_PROGRESS = 'test' in sys.argv
if TESTS_IN_PROGRESS:
    STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'
    AWS_STORAGE_BUCKET_NAME = 'blender-studio-test'
