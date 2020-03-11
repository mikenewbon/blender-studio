import os
from typing import List

# Enable to use OAuth without https during local development
import braintree
from dateutil.relativedelta import relativedelta

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SECRET_KEY = '7ijgr7*_l=x^f0!((j!*sdfsdfsdf*xfbf3vcz0=#!5aai85$h3ck6l9m3c'
DEBUG = True
ALLOWED_HOSTS: List[str] = ['studio.local']

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

GATEWAYS = {
    'braintree': {
        'environment': braintree.Environment.Sandbox,
        'merchant_id': '-snip-',
        'public_key': '-snip-',
        'private_key': '-snip-',
        # Merchant Account IDs for different currencies.
        # Configured in Braintree: Account → Merchant Account Info.
        'merchant_account_ids': {
            'EUR': 'merchant-account-id-for-eur',
            'USD': 'merchant-account-id-for-usd',
        },
    },
    # No settings, but a key is required here to activate the gateway.
    'bank': {},
}

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

# The system user from looper/fixtures/systemuser.json. This user is required
# for logging things in the admin history (those log entries always need to
# have a non-NULL user ID).
LOOPER_SYSTEM_USER_ID = 1

# Convertion rates from the given rate to euros.
# This allows us to express the foreign currency in €.
LOOPER_CONVERTION_RATES_FROM_EURO = {
    'EUR': 1.0,
    'USD': 1.15,
}

LOOPER_MONEY_LOCALE = 'en_US.UTF-8'

SUPPORTED_CURRENCIES = {'EUR', 'USD'}

# Get the latest from https://dev.maxmind.com/geoip/geoip2/geolite2/. Note that you should check
# whether we are allowed to redistribute the file according to the new license (per 2020) if you
# want to check the file into the repository.
GEOIP2_DB = '/path/to/GeoLite2-Country.mmdb'

GOOGLE_RECAPTCHA_SITE_KEY = '-snip-'
GOOGLE_RECAPTCHA_SECRET_KEY = '-snip-'
