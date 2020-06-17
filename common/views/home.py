from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from films.models import Film
from training.models import Training


@require_safe
def home(request: HttpRequest) -> HttpResponse:
    context = {
        'sample_films': Film.objects.order_by('-date_created')[:3],
        'sample_trainings': Training.objects.order_by('-is_featured')[:3],
    }

    return render(request, 'common/home.html', context)


@require_safe
def welcome(request: HttpRequest) -> HttpResponse:
    context = {
        'sample_films': Film.objects.order_by('-date_created')[:3],
        'sample_trainings': Training.objects.order_by('-is_featured')[:3],
    }

    return render(request, 'common/welcome.html', context)
