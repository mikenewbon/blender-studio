from django.http.request import HttpRequest

import training_main.types
from training_main import queries
from training_main import responses
from training_main.views.common import training_model_to_template_type
from training_main.views.decorators import login_required


def home(request: HttpRequest) -> training_main.types.TypeSafeTemplateResponse:
    if request.user.is_authenticated:
        return home_authenticated(request)
    else:
        return home_not_authenticated(request)


@login_required
def home_authenticated(request: HttpRequest) -> training_main.types.TypeSafeTemplateResponse:
    favorited_trainings = queries.trainings.favorited(user=request.user)
    recently_watched_trainings = queries.trainings.recently_watched(user=request.user)
    all_trainings = queries.trainings.all()

    return responses.home.home_authenticated(
        request,
        favorited_trainings=[
            training_model_to_template_type(training) for training in favorited_trainings
        ],
        recently_watched_trainings=[
            training_model_to_template_type(training) for training in recently_watched_trainings
        ],
        all_trainings=[training_model_to_template_type(training) for training in all_trainings],
    )


def home_not_authenticated(request: HttpRequest) -> training_main.types.TypeSafeTemplateResponse:
    all_trainings = queries.trainings.all()
    return responses.home.home_not_authenticated(
        request,
        all_trainings=[training_model_to_template_type(training) for training in all_trainings],
    )
