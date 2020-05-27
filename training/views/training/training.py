from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.views.decorators.http import require_safe

from common.typed_templates.errors import not_found
from common.typed_templates.types import TypeSafeTemplateResponse
from subscriptions.decorators import subscription_required
from training import queries
from training.typed_templates.training import training as typed_template_training
from training.views.common import navigation_to_template_type, training_model_to_template_type


@require_safe
@login_required
# @subscription_required
def training(request: HttpRequest, *, training_slug: str) -> TypeSafeTemplateResponse:
    result = queries.trainings.from_slug(user_pk=request.user.pk, training_slug=training_slug)

    if result is None:
        return not_found(request)
    else:
        training, favorited = result
        navigation = queries.trainings.navigation(user_pk=request.user.pk, training_pk=training.pk)
        return typed_template_training(
            request,
            training=training_model_to_template_type(training, favorited),
            navigation=navigation_to_template_type(
                *navigation, user=request.user, current='overview'
            ),
        )
