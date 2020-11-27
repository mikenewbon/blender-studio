from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from common.queries import has_active_subscription
from films.models import Film
from films.queries import get_production_logs_page


@require_safe
def production_logs_page(request: HttpRequest, film_pk: int) -> HttpResponse:
    film = get_object_or_404(Film, id=film_pk, is_published=True)
    page_number = request.GET.get('page')
    per_page = request.GET.get('per_page')
    context = {
        'user_can_view_asset': (
            request.user.is_authenticated and has_active_subscription(request.user)
        ),
        'film': film,
        'production_logs_page': get_production_logs_page(film, page_number, per_page),
        'show_more_button': True,
    }

    return render(request, 'films/components/activity_feed.html', context)
