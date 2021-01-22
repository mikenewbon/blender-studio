"""Implement webhook handlers."""
from typing import Any, Dict
import hashlib
import hmac
import json
import logging

from background_task import background
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest
from django.http.request import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from users.queries import set_groups_from_roles
from users.blender_id import BIDSession

bid = BIDSession()


logger = logging.getLogger(__name__)
WEBHOOK_MAX_BODY_SIZE = 1024 * 10  # 10 kB is large enough


@csrf_exempt
@require_POST
def user_modified_webhook(request: HttpRequest) -> HttpResponse:
    """Handle user modified request sent by Blender ID.

    Payload is expected to have the following format:
        {
            "avatar_changed": false,
            "email": "newmail@example.com",
            "full_name": "John Doe",
            "id": 2,
            "old_email": "mail@example.com",
            "roles": ["role1", "role2"],
        }
    """
    hmac_secret = settings.BLENDER_ID['WEBHOOK_USER_MODIFIED_SECRET']

    # Check the content type
    if request.content_type != 'application/json':
        logger.info(f'unexpected content type {request.content_type}')
        return HttpResponseBadRequest('Unsupported Content-Type')

    # Check the length of the body
    content_length = int(request.headers['CONTENT_LENGTH'])
    if content_length > WEBHOOK_MAX_BODY_SIZE:
        return HttpResponse('Payload Too Large', status=413)
    body = request.body
    if len(body) != content_length:
        return HttpResponseBadRequest("Content-Length header doesn't match content")

    # Validate the request
    mac = hmac.new(hmac_secret, body, hashlib.sha256)
    req_hmac = request.headers.get('X-Webhook-HMAC', '')
    our_hmac = mac.hexdigest()
    if not hmac.compare_digest(req_hmac, our_hmac):
        logger.info(f'Invalid HMAC {req_hmac}, expected {our_hmac}')
        return HttpResponseBadRequest('Invalid HMAC')

    try:
        payload = json.loads(body)
        # TODO(anna) validate the payload
        logger.info('payload: %s', payload)
    except json.JSONDecodeError:
        logger.exception('Malformed JSON received')
        return HttpResponseBadRequest('Malformed JSON')

    handle_user_modified(payload)

    return HttpResponse(status=204)


@background()
def handle_user_modified(payload: Dict[Any, Any]) -> None:
    """Handle payload of a user modified webhook, updating User when necessary."""
    oauth_user_id = str(payload['id'])
    try:
        oauth_user_info = bid.get_oauth_user_info(oauth_user_id)
    except ObjectDoesNotExist:
        logger.warning(f'Cannot update user: no OAuth info found for ID {oauth_user_id}')
        return

    user = oauth_user_info.user

    if payload.get('date_deletion_requested'):
        user.request_deletion(payload['date_deletion_requested'])
        return

    try:
        if payload['email'] != user.email:
            user.email = payload['email']
            user.save(update_fields=['email'])
    except IntegrityError:
        logger.exception(f'Unable to update email for {user}: duplicate email')

    if payload['full_name'] != user.full_name:
        user.full_name = payload['full_name']
        user.save(update_fields=['full_name'])

    if payload.get('avatar_changed') or not user.image:
        bid.copy_avatar_from_blender_id(user=user)

    # Sync roles to groups
    group_names = payload.get('roles') or []
    set_groups_from_roles(user, group_names=group_names)

    # Attempt to update the username
    bid.update_username(user, oauth_user_id)

    # Attempt to update the badges
    bid.copy_badges_from_blender_id(user=user)
