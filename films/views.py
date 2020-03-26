from django.shortcuts import render

# Create your views here.
def index(request):

    context = {'films': 'filmslist '}
    return render(request, 'films/films_list.html', context)