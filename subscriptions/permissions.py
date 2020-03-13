from django.http import HttpRequest
from looper.models import Customer

from subscriptions.models import Organization, Subscriber


def can_change_customer(request: HttpRequest, customer: Customer) -> bool:
    if not request.user.is_authenticated:
        return False

    try:
        return customer.subscriber.user_id == request.user.id
    except Subscriber.DoesNotExist:
        pass

    try:
        return customer.organization.organization_users.filter(
            can_change_organization=True, user_id=request.user.id
        ).exists()
    except Organization.DoesNotExist:
        pass

    return False
