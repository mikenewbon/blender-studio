"""Various additions to template context, such as search and analytics credentials."""
from typing import Dict

from django.conf import settings
from django.http.request import HttpRequest


def search_client_config(request: HttpRequest) -> Dict[str, Dict[str, str]]:
    """Inject the MeiliSearch client configuration data into the template context."""
    return {
        'search_client_config': {
            'hostUrl': settings.MEILISEARCH_API_ADDRESS,
            'apiKey': settings.MEILISEARCH_PUBLIC_KEY,
        },
    }


def settings_analytics_id(request: HttpRequest) -> Dict[str, Dict[str, str]]:
    """Inject the Google Analytics data the template context."""
    return {'settings_analytics_id': settings.GOOGLE_ANALYTICS_TRACKING_ID}


def extra_context(request: HttpRequest) -> Dict[str, str]:
    """Injects some configuration values into template context."""
    return {
        'BLENDER_ID': {
            'BASE_URL': settings.BLENDER_ID['BASE_URL'],
        },
        'canonical_url': request.build_absolute_uri(request.path),
        'ADMIN_MAIL': settings.ADMIN_MAIL,
        'STORE_PRODUCT_URL': settings.STORE_PRODUCT_URL,
        'STORE_MANAGE_URL': settings.STORE_MANAGE_URL,
        'GOOGLE_RECAPTCHA_SITE_KEY': settings.GOOGLE_RECAPTCHA_SITE_KEY,
    }
