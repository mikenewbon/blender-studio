# noqa: D100
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from blog.queries import get_latest_post_revisions
from films.models import Film
from films.queries import get_random_featured_assets
from training.models import Training
from training.queries.sections import recently_watched
from training.views.common import recently_watched_sections_to_template_type


@require_safe
def home(request: HttpRequest) -> HttpResponse:
    """
    Render the home page of Blender Studio.

    **Context**:
        ``records``
            A paginator Page object with dictionaries representing recently created objects:
            instances of :model:`blog.Post`, :model:`ProductionLog`, or
            :model:`training.Training`. The dictionaries have the following keys:

            - 'pk': int - the primary key of the related object,
            - 'date_created': datetime - the date when the object was created,
            - 'obj_type': str - specifies the type (model) of the object,
            - 'object': a particular Model instance.

    **Template**
        :template:`common/home.html`
    """
    context = {
        'featured_trainings': Training.objects.filter(),
        'featured_film_assets': get_random_featured_assets(limit=8),
        'latest_posts': get_latest_post_revisions(limit=6),
        'recently_watched_sections': [],
    }
    if request.user.is_authenticated:
        recently_watched_sections = recently_watched(user_pk=request.user.pk)
        context['recently_watched_sections'] = recently_watched_sections_to_template_type(
            recently_watched_sections
        )

    return render(request, 'common/home.html', context)


@require_safe
def welcome(request: HttpRequest) -> HttpResponse:
    """
    Render the welcome page of Blender Studio.

    **Context**:
        ``featured_films``
            A queryset of films marked as featured.
        ``featured_trainings``
            A queryset of trainings marked as featured.

    **Template**
        :template:`common/welcome.html`
    """
    context = {
        'featured_films': Film.objects.filter(is_featured=True),
        'featured_trainings': Training.objects.filter(is_featured=True),
    }

    return render(request, 'common/welcome.html', context)
