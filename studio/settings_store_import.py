"""Extra settings just for ./manage.py import_store_data command."""
from studio.settings import *  # noqa: F403

# Django runs systems check that include connecting to all defined databases,
# and Store's backup will only be available intermittently, hence this separate settings file
# is here to avoid breaking runserver and other manage commands.
# Usage:
# DJANGO_SETTINGS_MODULE=studio.settings_store_import ./manage.py import_store_data
INSTALLED_APPS.extend([  # noqa: F405
    'wordpress',
    'store_import',
])
LOGGING['formatters'].update({  # noqa: F405
    'short': {'format': '%(funcName)s:%(lineno)s %(message)s'},
})
LOGGING['handlers'].update({  # noqa: F405
    'console_short': {
        'class': 'logging.StreamHandler',
        'formatter': 'short',
        'stream': 'ext://sys.stderr',
    },
})
LOGGING['loggers'].update({  # noqa: F405
    # 'django.db.backends': {'level': 'DEBUG', 'handlers': ['console']},
    'store_import': {'level': 'DEBUG', 'handlers': ['console_short'], 'propagate': False},
})
DATABASES.update({  # noqa: F405
    'store': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'store',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3307',
    },
})
DATABASE_ROUTERS = ['wordpress.router.WordpressRouter']
WP_DATABASE = 'store'
