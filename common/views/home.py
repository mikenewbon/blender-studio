from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from common.queries import get_activity_feed_page
from films.models import Film
from training.models import Training


@require_safe
def home(request: HttpRequest) -> HttpResponse:
    """
    Renders the home page of Blender Studio.

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
    context = {'records': get_activity_feed_page()}

    return render(request, 'common/home.html', context)


@require_safe
def welcome(request: HttpRequest) -> HttpResponse:
    """
    Renders the welcome page of Blender Studio.

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
