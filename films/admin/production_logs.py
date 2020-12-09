from typing import Optional, Any, Tuple
import datetime as dt
import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple, RelatedFieldWidgetWrapper
from django.contrib.auth import get_user_model
from django.db.models import ForeignKey, Q
from django.forms.models import ModelForm, ModelChoiceField
from django.http.request import HttpRequest
from django.utils import timezone
from django.utils.encoding import force_text

from common.mixins import AdminUserDefaultMixin, ViewOnSiteMixin
from films.admin.mixins import EditLinkMixin
from films.models import production_logs, Asset, Film

User = get_user_model()
log = logging.getLogger(__name__)


class _ErrorLoggingForm(ModelForm):
    def is_valid(self):
        log.info(force_text(self.errors))
        return super().is_valid()


def get_context(request: HttpRequest) -> Tuple[Any]:
    """Get film, log and entry from the given request, if available."""
    try:
        return Film.objects.get(id=int(request.GET.get('film'))), None, None
    except TypeError:
        try:
            object_id = request.resolver_match.kwargs['object_id']
            if request.resolver_match.url_name == 'films_productionlogentry_change':
                _entry = production_logs.ProductionLogEntry.objects.get(pk=object_id)
                return _entry.production_log.film, _entry.production_log, _entry
            elif request.resolver_match.url_name == 'films_productionlog_change':
                _log = production_logs.ProductionLog.objects.get(pk=object_id)
                return _log.film, _log, None
        except KeyError:
            pass
    return None, None, None


def get_film_assset_widget(rel_model, col_name) -> RelatedFieldWidgetWrapper:
    """Construct a multi-select widget for film assets."""
    rel = rel_model._meta.get_field(col_name).remote_field
    return RelatedFieldWidgetWrapper(
        FilteredSelectMultiple(verbose_name=col_name, is_stacked=False),
        rel,
        admin.site,
        # FIXME(anna): get `request.user.has_perm` here to control widget buttons somehow
        # can_add_related=True,
        # can_change_related=True,
    )


def get_film_asset_queryset(
    request,
    film: Optional[Film] = None,
    entry: Optional[production_logs.ProductionLogEntry] = None,
    log: Optional[production_logs.ProductionLog] = None,
):
    """Limit film asset selection to relevant assets."""
    asset_queryset = Asset.objects.all()
    asset_filters = Q(
        is_published=True,
        date_created__gte=timezone.now() - dt.timedelta(days=14),
        # Exclude assets already mentioned in production logs
        entry_asset__production_log_entry_id__isnull=True,
    )
    # Filter by film too, if possible
    if film:
        asset_filters = asset_filters & Q(film_id=film.id)
    if entry:
        # If changing an existing log entry, always include already linked assets.
        # Otherwise they aren't displayed in the widget as selected
        asset_filters = asset_filters | Q(id__in=entry.assets.all())
    if log:
        # If changing an existing log with entries inlined, always include already linked assets.
        # Otherwise they aren't displayed in the widget as selected
        asset_filters = asset_filters | Q(
            entry_asset__production_log_entry__production_log_id=log.pk
        )
    return asset_queryset.filter(asset_filters).order_by(
        'order', '-date_published', '-date_created'
    )


def get_film_assets_help_text(request, film: Optional[Film] = None) -> str:
    """Return a more detailed help test for film asset selection."""
    help_text_bits = (
        'Only recently created <b>published',
        "</b> assets that haven't been added to production logs show up here.",
        '<br>If nothing shows up, click on the '
        f'"Add" <img src="{settings.STATIC_URL}admin/img/icon-addlink.svg"> '
        'button to upload a new film asset',
    )
    if film:
        return f'{help_text_bits[0]} {film}{help_text_bits[1]}{help_text_bits[2]}'
    return ''.join(help_text_bits)


class LimitSelectionMixin:
    _entry = None
    _film = None
    _log = None

    def get_film_crew_queryset(self, request):
        """Limit selection to currently film crew."""
        crew_queryset = User.objects.exclude(film_crew__film_id__isnull=True)
        if self._film:
            # Limit selection to currently selected film crew, if possible
            crew_queryset = User.objects.filter(film_crew__film_id=self._film.id)
        return crew_queryset.distinct()

    def formfield_for_foreignkey(
        self, db_field: 'ForeignKey[Any, Any]', request: Optional[HttpRequest], **kwargs
    ) -> Optional[ModelChoiceField]:
        """Limit users to film crew members."""
        if db_field.name == 'author':
            kwargs['queryset'] = self.get_film_crew_queryset(request)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(production_logs.ProductionLogEntry)
class ProductionLogEntryAdmin(AdminUserDefaultMixin, LimitSelectionMixin, admin.ModelAdmin):
    class ProductionLogEntryAdminForm(ModelForm):
        """Override the ModelForm to avoid polluting ModelForm.declared_fields."""

    form = ProductionLogEntryAdminForm
    date_hierarchy = 'production_log__start_date'
    list_display = ['__str__', 'production_log']
    list_filter = [
        'production_log__film',
        'production_log',
        'production_log__start_date',
    ]
    search_fields = [
        'production_log__name',
    ]
    readonly_fields = ['date_created', 'legacy_id']

    def get_fields(self, request, obj=None, **kwargs):
        """Add additional fields, like M2M film assets.

        Because `request` isn't passed to the Form init, this appears to be the least
        painful way to have a working multi-select widget, while overriding
        its queryset depending on `request` at the same time.
        """
        fields = super().get_fields(request, obj, **kwargs)
        self._film, self._log, self._entry = get_context(request)
        asset_field = forms.ModelMultipleChoiceField(
            queryset=get_film_asset_queryset(request, film=self._film, entry=self._entry),
            widget=get_film_assset_widget(self.model, 'assets'),
            help_text=get_film_assets_help_text(request, self._film),
            initial=obj and [_.pk for _ in obj.assets.all()] or None,
        )
        self.form.declared_fields.update({'assets': asset_field})
        return fields


class ProductionLogEntryInline(
    AdminUserDefaultMixin, EditLinkMixin, LimitSelectionMixin, admin.StackedInline
):
    class _ProductionLogEntryInlineForm(LimitSelectionMixin, forms.ModelForm):
        assets = forms.ModelMultipleChoiceField(
            queryset=None,  # Will be set when request is available
            widget=get_film_assset_widget(production_logs.ProductionLogEntry, 'assets'),
        )

    def get_formset(self, request, obj=None, *args, **kwargs):
        """Overrides form field attributes of the production log entry assets."""
        formset = super().get_formset(request, obj, *args, **kwargs)
        formset._film, formset._log, formset._entry = get_context(request)

        asset_field = formset.form.declared_fields['assets']
        asset_field.queryset = get_film_asset_queryset(request, film=formset._film, log=obj)
        asset_field.help_text = get_film_assets_help_text(request, formset._film)
        return formset

    model = production_logs.ProductionLogEntry
    form = _ProductionLogEntryInlineForm
    show_change_link = True
    extra = 0
    readonly_fields = ['date_created', 'legacy_id']


@admin.register(production_logs.ProductionLog)
class ProductionLogAdmin(
    AdminUserDefaultMixin, LimitSelectionMixin, ViewOnSiteMixin, admin.ModelAdmin
):
    form = _ErrorLoggingForm
    inlines = [ProductionLogEntryInline]
    date_hierarchy = 'start_date'
    list_display = ['__str__', 'user', 'name', 'start_date', 'view_link']
    list_editable = ['name', 'start_date']
    list_filter = ['film', 'start_date']
    search_fields = [
        'name',
    ]
    readonly_fields = ['date_created']
    fieldsets = (
        (None, {'fields': ['film', 'name', 'start_date']}),
        ('Summary', {'fields': ['thumbnail', 'youtube_link', 'author', 'summary']}),
    )
