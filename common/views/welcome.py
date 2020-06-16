from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Film
from training.models import Training


@require_safe
def welcome(request: HttpRequest) -> HttpResponse:
    context = {
        'sample_films': Film.objects.all()[:3],
        'sample_trainings': Training.objects.all()[:3],
    }

    return render(request, 'common/welcome.html', context)
