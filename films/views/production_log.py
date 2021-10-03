"""Displays production log pages."""
from django.db.models.query import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls.base import reverse
from django.views.generic import dates, detail

from common.queries import has_active_subscription
from films.models import Film, ProductionLog
from films.queries import (
    get_next_production_log,
    get_previous_production_log,
    get_production_logs,
    should_show_landing_page,
)


def _get_shared_context(request):
    film_slug = request.resolver_match.kwargs['film_slug']
    film = get_object_or_404(Film, slug=film_slug, is_published=True)
    return {
        'film': film,
        'user_can_view_asset': (
            request.user.is_authenticated and has_active_subscription(request.user)
        ),
        'user_can_edit_production_log': (
            request.user.is_staff and request.user.has_perm('films.change_productionlog')
        ),
        'user_can_edit_production_log_entry': (
            request.user.is_staff and request.user.has_perm('films.change_productionlogentry')
        ),
        'user_can_edit_asset': (
            request.user.is_staff and request.user.has_perm('films.change_asset')
        ),
    }


class LandingPageMixin:
    """Possibly redirect to film landing page instead of showing the content."""

    def render_to_response(self, context, *args, **kwargs):
        """Redirect non-subscribers to film landing page if this film is configured so."""
        film = context.get('film')
        if film and should_show_landing_page(self.request, film):
            return redirect(
                reverse('film-detail', kwargs={'film_slug': film.slug}), permanent=False
            )
        return super().render_to_response(context, *args, **kwargs)


class ProductionLogDetailView(LandingPageMixin, detail.DetailView):
    """Display a single production log."""

    model = ProductionLog
    context_object_name = 'production_log'

    def get_object(self) -> ProductionLog:
        """Check that retrieved log belongs to the right film, otherwise 404."""
        object_ = super().get_object()
        film_slug = self.request.resolver_match.kwargs['film_slug']
        if object_.film.slug != film_slug:
            raise Http404()
        return object_

    def get_context_data(self, **kwargs):
        """Add film production logs context."""
        context = super().get_context_data(**kwargs)
        context.update(_get_shared_context(self.request))
        production_log = context['production_log']
        film_production_logs = list(
            production_log.film.production_logs.order_by(*ProductionLog._meta.ordering).all()
        )
        context['previous'] = get_previous_production_log(film_production_logs, production_log)
        context['next'] = get_next_production_log(film_production_logs, production_log)
        if self.request.user.is_authenticated:
            context['user_has_production_credit'] = self.request.user.production_credits.filter(film=self.object.film)

        return context


class _ProductionLogViewMixin:
    allow_empty = False
    allow_future = False
    date_field = "start_date"
    date_list_period = 'month'
    make_object_list = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_shared_context(self.request))
        # Make sure `date_list` is an actual list, not a QuerySet, otherwise `|last` won't work
        if 'date_list' in context:
            context['date_list'] = list(context['date_list'])
        if self.request.user.is_authenticated:
            film_slug = self.request.resolver_match.kwargs['film_slug']
            film = get_object_or_404(Film, slug=film_slug, is_published=True)
            context['user_has_production_credit'] = self.request.user.production_credits.filter(film=film)
        return context

    def get_queryset(self) -> QuerySet:
        """Return production log queryset based on request."""
        film_slug = self.request.resolver_match.kwargs['film_slug']
        film = get_object_or_404(Film, slug=film_slug, is_published=True)
        return get_production_logs(film)


class ProductionLogView(_ProductionLogViewMixin, LandingPageMixin, dates.ArchiveIndexView):
    """Displays the latest production logs for the :model:`films.Film` with the given slug.

    Also fetches the related log entries (:model:`films.ProductionLogEntry`), and
    the assets (:model:`films.Asset`) they contain.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``latest_month``
        A list of production logs available in the most recent month
    ``object_list``
        A list of all production logs
    ``date_list``
        A list of `datetime`s (one per month) that have logs available
    ``user_can_edit_production_log``
        A bool specifying whether the current user should be able to edit
        :model:`films.ProductionLog` items displayed in the Weeklies section of the page.
    ``user_can_edit_production_log_entry``
        A bool specifying whether the current user should be able to edit
        :model:`films.ProductionLogEntry` items in the production logs.
    ``user_can_edit_asset``
        A bool specifying whether the current user should be able to edit
        :model:`films.Asset` items displayed in the production log entries.

    **Template:**

    :template:`films/productionlog.html`
    """

    template_name_suffix = ''

    def get_context_data(self, **kwargs):
        """Add logs from the latest (not necessarily the last) month to the template context."""
        context = super().get_context_data(**kwargs)
        queryset = context['object_list']
        latest_month = []
        latest = queryset[0] if queryset.count() else None
        for log in queryset:
            if log.start_date.strftime('%Y%m') != latest.start_date.strftime('%Y%m'):
                break
            latest_month.append(log)
        context['latest_month'] = latest_month
        return context


class ProductionLogMonthView(_ProductionLogViewMixin, LandingPageMixin, dates.MonthArchiveView):
    """Display film production logs paginated by month.

    Also fetches the related log entries (:model:`films.ProductionLogEntry`), and
    the assets (:model:`films.Asset`) they contain.

    **Context:**

    ``film``
        An instance of :model:`films.Film`.
    ``object_list``
        A list of logs for the given month
    ``date_list``
        A list of `datetime`s (one per month) that have logs available
    ``next_month``
        `datetime` representing a next month in which logs are available
    ``previous_month``
        `datetime` representing a previous month in which logs are available
    ``user_can_edit_production_log``
        A bool specifying whether the current user should be able to edit
        :model:`films.ProductionLog` items displayed in the Weeklies section of the page.
    ``user_can_edit_production_log_entry``
        A bool specifying whether the current user should be able to edit
        :model:`films.ProductionLogEntry` items in the production logs.
    ``user_can_edit_asset``
        A bool specifying whether the current user should be able to edit
        :model:`films.Asset` items displayed in the production log entries.

    **Template:**

    :template:`films/productionlog_month.html`
    """

    template_name_suffix = '_month'

    def get_context_data(self, **kwargs):
        """Keep `date_list` exactly the same as in ProductionLogView.

        By default, MonthArchiveView will only add `next_month`, `previous_month ` instead.
        """
        context = super().get_context_data(**kwargs)
        date_list = self.get_date_list(self.get_dated_queryset(), ordering='DESC')
        # Make sure `date_list` is an actual list, not a QuerySet, otherwise `|last` won't work
        context['date_list'] = list(date_list)
        return context
