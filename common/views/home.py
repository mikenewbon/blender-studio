from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Film
from training.models import Training


@require_safe
def home(request: HttpRequest) -> HttpResponse:
    context = {
        'sample_films': Film.objects.filter(is_featured=True)[:2],
        'sample_trainings': Training.objects.filter(is_featured=True)[:2],
    }

    return render(request, 'common/home.html', context)


@require_safe
def welcome(request: HttpRequest) -> HttpResponse:
    context = {
        'sample_films': Film.objects.filter(is_featured=True)[:3],
        'sample_trainings': Training.objects.filter(is_featured=True)[:3],
    }

    return render(request, 'common/welcome.html', context)
