from typing import Tuple
from urllib.parse import quote as urlquote
import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_permission_codename, get_user_model
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from films.models import assets, collections, films
from static_assets.models import static_assets
from common import mixins
import search.signals

User = get_user_model()
logger = logging.getLogger(__name__)


asset_fieldsets = (
    (None, {'fields': (('name', 'view_link'), 'description')}),
    (None, {'fields': (('film', 'collection'),)}),
    (
        None,
        {
            'fields': (
                ('is_published', 'is_featured', 'is_free', 'is_spoiler'),
                'contains_blend_file',
            )
        },
    ),
    (None, {'fields': (('category', 'tags'),)}),
    (None, {'fields': ('date_published',)}),
)


def _clear_messages(request):
    list(messages.get_messages(request))


@admin.register(assets.Asset)
class AssetAdmin(mixins.ThumbnailMixin, mixins.ViewOnSiteMixin, admin.ModelAdmin):
    # asset slugs aren't currently in use and were prepopulate
    # during import from previous version of Blender Cloud
    # prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['view_link', 'slug']
    list_display = [
        'view_thumbnail',
        '__str__',
        'date_published',
        'order',
        'film',
        'collection',
        'view_link',
    ]
    list_display_links = ('view_thumbnail', '__str__')
    list_filter = [
        'film',
        'category',
        'is_published',
        'is_featured',
        'static_asset__source_type',
    ]
    search_fields = [
        'name',
        'film__title',
        'collection__name',
        'slug',
        'static_asset__slug',
        'static_asset__source',
    ]
    fieldsets = (
        (None, {'fields': ('static_asset',)}),
        *asset_fieldsets,
    )
    autocomplete_fields = ['static_asset', 'attachments', 'collection']
    ordering = ('-date_created',)

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[assets.Asset]':
        """Select extra related data in the default queryset."""
        return super().get_queryset(request).select_related('film', 'collection__film')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit collections to the current film."""
        if db_field.name == 'collection':
            try:
                object_id = request.resolver_match.kwargs['object_id']
            except KeyError:
                return super().formfield_for_foreignkey(db_field, request, **kwargs)
            film = assets.Asset.objects.get(pk=object_id).film
            kwargs['queryset'] = collections.Collection.objects.filter(film=film).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    actions = [search.signals.reindex]


@admin.register(collections.Collection)
class CollectionAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    list_display = ['__str__', 'film', 'order', 'parent', 'view_link']
    list_filter = ['film']
    search_fields = ['name', 'film__title', 'slug']
    autocomplete_fields = ['parent', 'user', 'film']
    readonly_fields = ['slug']
    ordering = ('-date_created',)
    fieldsets = (
        (None, {'fields': (('film', 'parent'),)}),
        (None, {'fields': (('name', 'thumbnail_aspect_ratio'), 'text')}),
        (None, {'fields': ('thumbnail',)}),
        (None, {'fields': (('user', 'order'),)}),
        (None, {'fields': ('slug',)}),
    )

    def response_delete(self, request, obj_display, obj_id):
        """Support ?next= redirect."""
        response = super().response_delete(request, obj_display, obj_id)
        if request.GET.get('next'):
            _clear_messages(request)
            return redirect(request.GET['next'])
        return response

    def response_add(self, request, obj, **kwargs):
        """Allow redirecting to "view on site" URL of the newly added object."""
        response = super().response_add(request, obj, **kwargs)
        if request.GET.get('next-view-link'):
            _clear_messages(request)
            return redirect(obj.url)
        return response


class FilmCrewInlineAdmin(admin.TabularInline):
    model = films.Film.crew.through
    verbose_name_plural = 'Crew'
    autocomplete_fields = ['user']


@admin.register(films.Film)
class FilmAdmin(mixins.ViewOnSiteMixin, admin.ModelAdmin):
    search_fields = ['title', 'slug']
    list_display = ('title', 'view_link')
    prepopulated_fields = {'slug': ('title',)}
    inlines = (FilmCrewInlineAdmin,)


class AssetFromFileInline(
    mixins.AdminUserDefaultMixin, mixins.ViewOnSiteMixin, admin.StackedInline
):
    class _Form(forms.ModelForm):
        def __init__(self, *args, **kwargs):
            """Unrequire required fields: they will be filled in based on StaticAsset form."""
            super().__init__(*args, **kwargs)
            for name in ('name', 'category'):
                self.fields[name].required = False

        def get_initial_for_field(self, field, name, **kwargs):
            initial = super().get_initial_for_field(field, name, **kwargs)
            prepopulated_fields = {
                'is_published': bool,
                'is_featured': bool,
                'collection': int,
                'film': int,
            }
            if (
                self.request.method == 'GET'
                and name in prepopulated_fields
                and name in self.request.GET
            ):
                try:
                    type_ = prepopulated_fields[name]
                    initial = type_(self.request.GET[name])
                except ValueError:
                    logger.exception('Invalid initial parameter for %s', name)
            return initial

    form = _Form
    model = assets.Asset
    # Changes title of the inline formset
    verbose_name_plural = 'Film asset details'
    # Changes title of each separate inline inside the inline formset
    verbose_name = 'Describe this film asset'
    fieldsets = asset_fieldsets
    extra = 1
    max_num = 1
    readonly_fields = ('view_link',)
    autocomplete_fields = ('collection', 'film')

    def get_formset(self, request, obj=None, **kwargs):
        """Pass request to the inline form."""
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.request = request
        return formset


class NewAsset(static_assets.StaticAsset):
    """Same as the other StaticAsset, but allows us to create a different admin form for it.

    N.B.: a proxy model also adds an empty migration, a new ContentType and new set of permissions.
    All three are useless but unavoidable.
    """

    class Meta:
        proxy = True


@admin.register(NewAsset)
class NewAssetAdmin(mixins.AdminUserDefaultMixin, admin.ModelAdmin):
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Limit contributors to film crew, if this is an existing film asset."""
        if db_field.name == 'contributors':
            try:
                film_id = request.GET.get('film')
                film = films.Film.objects.get(id=film_id)
                kwargs['queryset'] = film.crew.all()
            except Exception:
                logger.exception('Unable to limit users contributors queryset')
                kwargs['queryset'] = User.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_view_permission(self, request, obj=None):
        """Inherit permission from the parent Asset model.

        Proxy models require new permissions to be created, they don't
        inherit parent model's permissions.
        See https://code.djangoproject.com/ticket/11154 for more details.
        """
        opts = assets.Asset._meta
        codename = get_permission_codename('view', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_add_permission(self, request):
        """Inherit permission from the parent Asset model."""
        opts = assets.Asset._meta
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_change_permission(self, request, obj=None):
        """Inherit permission from the parent Asset model."""
        opts = assets.Asset._meta
        codename = get_permission_codename('change', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_delete_permission(self, request, obj=None):
        """Inherit permission from the parent Asset model."""
        opts = assets.Asset._meta
        codename = get_permission_codename('delete', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_module_permission(self, request):
        """Don't show this model in the admin sections.

        It's only needed for adding and editing, not listing.
        """
        return False

    class _Form(forms.ModelForm):
        def __init__(self, data=None, files=None, **kwargs):
            """Make source file required."""
            super().__init__(data, files, **kwargs)
            for name in ('source',):
                self.fields[name].required = True

    form = _Form
    model = NewAsset
    inlines = [AssetFromFileInline]
    # FIXME(anna): Django 3.2 supports filters for autocomplete_fields
    # autocomplete_fields = ['contributors']
    fieldsets = (
        (
            'Upload a file',
            {'fields': (('source', 'contributors'),)},
        ),
        (
            'Add a thumbnail (only required for production files)',
            {'fields': ('thumbnail',)},
        ),
    )

    def save_related(self, request, form, formsets, change):
        """Fill film asset fields based on the newly uploaded file."""
        if not change:
            static_asset: static_assets.StaticAsset = form.instance
            assert isinstance(static_asset, NewAsset), static_asset.__class__
            inline_form = None
            for formset in formsets:
                inline_form = formset.forms[0]
            assert isinstance(inline_form, AssetFromFileInline.form), inline_form.__class__
            film_asset: assets.Asset = inline_form.instance
            assert isinstance(film_asset, assets.Asset), film_asset.__class__

            # Set name based on original file name
            if not film_asset.name:
                film_asset.name = static_asset.original_filename
            # Set category (this might not be useful at all FIXME)
            if not film_asset.category:
                category = assets.AssetCategory.production_file
                if static_asset.source_type == static_assets.StaticAssetFileTypeChoices.image:
                    category = assets.AssetCategory.artwork
                film_asset.category = category

        super().save_related(request, form, formsets, change)

    def _preserve_initial_get_params(self, request, response):
        url_params = request.GET.urlencode()
        if url_params:
            redirect_url = f'{response.url}?{url_params}'
            if '?' in response.url:
                redirect_url = f'{response.url}&{url_params}'
            return HttpResponseRedirect(redirect_url)
        return response

    def _get_redirect_url(self, obj) -> Tuple[str, bool]:
        redirect_url = reverse('admin:films_newasset_change', kwargs={'object_id': obj.pk})
        film_asset = obj.assets.first()
        if film_asset and film_asset.is_published:
            return film_asset.url, True
        return redirect_url, False

    def response_add(self, request, obj, **kwargs):
        """Redirect to editing the newly uploaded asset in the same form."""
        if "_addanother" in request.POST:
            response = super().response_add(request, obj, **kwargs)
            return self._preserve_initial_get_params(request, response)
        elif "_continue" in request.POST or (
            # Redirecting after "Save as new".
            "_saveasnew" in request.POST
            and self.save_as_continue
            and self.has_change_permission(request, obj)
        ):
            response = super().response_add(request, obj, **kwargs)
            return self._preserve_initial_get_params(request, response)

        redirect_url, back_to_site = self._get_redirect_url(obj)
        if not back_to_site:
            opts = assets.Asset._meta
            msg_dict = {'name': opts.verbose_name, 'obj': str(obj)}
            msg = 'The {name} “{obj}” was added successfully.'
            self.message_user(request, format_html(msg, **msg_dict), messages.SUCCESS)
        return redirect(redirect_url)

    def response_change(self, request, obj, **kwargs):
        """Stay on the editing page and display a success message."""
        if "_addanother" in request.POST:
            response = super().response_change(request, obj, **kwargs)
            return self._preserve_initial_get_params(request, response)
        elif "_continue" in request.POST:
            response = super().response_change(request, obj, **kwargs)
            return self._preserve_initial_get_params(request, response)

        redirect_url, back_to_site = self._get_redirect_url(obj)
        if not back_to_site:
            opts = assets.Asset._meta
            msg_dict = {
                'name': opts.verbose_name,
                'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
            }
            msg = format_html('The {name} “{obj}” was changed successfully.', **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
        return redirect(redirect_url)
