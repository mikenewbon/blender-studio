from django.shortcuts import render

def index(request):

    context = {'films': 'filmslist '}
    return render(request, 'films/films_list.html', context)

def spring(request):

    context = {'films': 'spring '}
    return render(request, 'films/spring/spring.html', context)

def coffee_run(request):

    context = {'films': 'about '}
    return render(request, 'films/coffee-run/coffee-run.html', context)

def about(request):

    context = {'films': 'about '}
    return render(request, 'films/coffee-run/about.html', context)

def weeklies(request):

    context = {'films': 'weeklies '}
    return render(request, 'films/coffee-run/weeklies.html', context)

def gallery(request):

    context = {'films': 'about '}
    return render(request, 'films/coffee-run/gallery.html', context)
