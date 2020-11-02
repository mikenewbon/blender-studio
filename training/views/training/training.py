"""Views related to training."""
from django.http.request import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_safe

# from subscriptions.decorators import subscription_required
from common.typed_templates.errors import not_found
from common.typed_templates.types import TypeSafeTemplateResponse
from training import queries
from training.typed_templates.training import training as typed_template_training
from training.views.common import navigation_to_template_type, training_model_to_template_type
from training.models import Training, TrainingStatus, TrainingFlatPage


@require_safe
# @subscription_required
def training(request: HttpRequest, *, training_slug: str) -> TypeSafeTemplateResponse:
    """Display a training with a given slug."""
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


@require_safe
def flatpage(request: HttpRequest, training_slug: str, page_slug: str) -> HttpResponse:
    """
    Display a flatpage of the :model:`trainings.Training` specified by the given slug.

    **Context:**

    ``training``
        A :model:`trainings.Training` instance; the training that the flatpage belongs to.
    ``flatpage``
        A :model:`trainings.TrainingFlatPage` instance.
    ``user_can_edit_training``
        A bool specifying whether the current user is able to edit the
        :model:`trainings.Training` to which the page belongs.
    ``user_can_edit_flatpage``
        A bool specifying whether the current user is able to edit the
        :model:`trainings.TrainingFlatPage` displayed in the page.

    **Template:**

    :template:`training/flatpage.html`
    """
    training = get_object_or_404(Training, slug=training_slug, status=TrainingStatus.published)
    flatpage = get_object_or_404(TrainingFlatPage, training=training, slug=page_slug)
    context = {
        'training': training,
        'flatpage': flatpage,
        'user_can_edit_training': (
            request.user.is_staff and request.user.has_perm('trainings.change_training')
        ),
        'user_can_edit_flatpage': (
            request.user.is_staff and request.user.has_perm('trainings.change_trainingflatpage')
        ),
    }
    return render(request, 'training/flatpage.html', context)
