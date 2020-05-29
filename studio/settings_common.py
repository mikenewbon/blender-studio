import pathlib

import jinja2

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

# Application definition

INSTALLED_APPS = [
    'comments',
    'common',
    'films',
    'subscriptions',
    'training',

    'looper',
    'blender_id_oauth_client',
    'pipeline',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
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
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [
            str(BASE_DIR / 'training/templates'),
            str(BASE_DIR / 'comments/templates'),
            str(BASE_DIR / 'common/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'training.context_processors.enums',
            ],
            'undefined': jinja2.StrictUndefined,
            'environment': 'common.jinja2.environment',
            'extensions': ['pipeline.jinja2.PipelineExtension'],
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
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
        'vendor': {
            'source_filenames': [
                'common/scripts/vendor/popper.min.js',
                'common/scripts/vendor/jquery-3.4.1.min.js',
                'common/scripts/vendor/bootstrap.min.js',
                'common/scripts/vendor/plyr.polyfilled.min.js',
                'common/scripts/vendor/js.cookie-2.2.1.min.js',
            ],
            'output_filename': 'js/vendor.js',
            'extra_context': {'async': False, 'defer': False},
        },
    },
    'STYLESHEETS': {
        'training': {
            'source_filenames': ['training/styles/main.scss'],
            'output_filename': 'css/training.css',
            'extra_context': {'media': 'screen,projection', 'charset': 'utf-8'},
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
    'disable_existing_loggers': True,
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
    'root': {'level': 'WARNING', 'handlers': ['console']},
}

SITE_ID = 1
