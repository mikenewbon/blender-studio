from django.http.request import HttpRequest

import training_main.types
from training_main import responses, queries
from training_main.views.decorators import login_required


@login_required
def training(
    request: HttpRequest, *, training_slug: str
) -> training_main.types.TypeSafeTemplateResponse:
    result = queries.trainings.from_slug_with_chapters(training_slug)

    if result is None:
        return responses.errors.not_found(request)
    else:
        training, chapters = result
        return responses.trainings.training.training(request, training=training, chapters=chapters)
