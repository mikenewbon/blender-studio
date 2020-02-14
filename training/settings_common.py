import pathlib

import jinja2

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

# Application definition

INSTALLED_APPS = [
    'training_main',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pipeline',
    'blender_id_oauth_client',
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

ROOT_URLCONF = 'training.urls'

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATIC_ROOT = BASE_DIR / 'public/static'
MEDIA_ROOT = BASE_DIR / 'public/media'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [str(BASE_DIR / 'training_main/templates')],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'undefined': jinja2.StrictUndefined,
            'environment': 'training_main.jinja2.environment',
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

WSGI_APPLICATION = 'training.wsgi.application'

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
    # 'PIPELINE_ENABLED': False,
    'JS_COMPRESSOR': 'pipeline.compressors.jsmin.JSMinCompressor',
    'CSS_COMPRESSOR': 'pipeline.compressors.NoopCompressor',
    'JAVASCRIPT': {},
    'STYLESHEETS': {
        'cloud': {
            'source_filenames': ['training_main/styles/cloud/cloud.scss'],
            'output_filename': 'css/cloud.css',
            'extra_context': {'media': 'screen,projection'},
        },
    },
    'COMPILERS': ('libsasscompiler.LibSassCompiler',),
    'DISABLE_WRAPPER': True,
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
    'loggers': {'training': {'level': 'DEBUG'}, 'training_main': {'level': 'DEBUG'}},
    'root': {'level': 'WARNING', 'handlers': ['console']},
}
