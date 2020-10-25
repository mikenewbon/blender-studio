import responses
from django.conf import settings


def mock_blender_id_responses() -> None:
    """Set up mock responses of Blender ID service."""
    base_url = settings.BLENDER_ID['BASE_URL']
    responses.add(
        responses.GET,
        f'{base_url}api/user/2/avatar',
        status=302,
        headers={'Location': f'{base_url}media/cache/1c/da/1cda54d605799b1f4b0dc080.jpg',},
    )
    responses.add(
        responses.GET,
        f'{base_url}api/me',
        json={
            'id': 2,
            'full_name': 'ⅉane ⅅoe',
            'email': 'jane@example.com',
            'nickname': 'ⅉanedoe',
            # N.B.: roles format here differs from one in user-modified webhook payload.
            'roles': {'dev_core': True, 'cloud_has_subscription': True, 'cloud_subscriber': True,},
        },
    )
    with open('common/static/common/images/blank-profile-pic.png', 'rb') as out:
        responses.add(
            responses.GET,
            'http://id.local:8000/media/cache/1c/da/1cda54d605799b1f4b0dc080.jpg',
            body=out,
            stream=True,
        )
