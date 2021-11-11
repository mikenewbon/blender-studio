"""Characters and character version views."""
from typing import Optional, List

from django.contrib.redirects.models import Redirect
from django.db import models
from django.db.models.query import QuerySet
from django.http import Http404
from django.views.generic import ListView, DetailView
from django.views.generic.base import RedirectView

from characters.models import Character, CharacterVersion, CharacterShowcase
from characters.queries import (
    get_characters,
    get_character,
    get_character_version,
    get_character_showcase,
)
from comments.models import Comment
from comments.queries import get_annotated_comments
from comments.views.common import comments_to_template_type
from stats.models import StaticAssetView


class CharacterList(ListView):
    """Show all characters."""

    model = Character
    context_object_name = 'characters'

    def get_queryset(self) -> QuerySet:
        """Return all characters, it's up to the template to display them depending on the user."""
        characters = get_characters().all()
        # Assign 'liked' attributes
        if self.request.user.is_authenticated:
            liked_character_ids = {c.character_id for c in self.request.user.liked_characters.all()}
            for character in characters:
                character.liked = character.pk in liked_character_ids
        return characters


class CharacterDetail(RedirectView):
    """Redirect to latest published character version."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        """Redirect to latest published character version."""
        filter_published = (
            {'is_published': True}
            if not self.request.user.is_staff and not self.request.user.is_superuser
            else {}
        )
        try:
            character = get_character(slug=kwargs['slug'], **filter_published)
            latest_version = character.versions.filter(**filter_published).first()
            if not latest_version:
                raise Http404()
            return latest_version.get_absolute_url()
        except Character.DoesNotExist:
            # Any other old Cloud endpoints are maintained via Redirects
            existing_redirect = Redirect.objects.filter(old_path=self.request.path).first()
            if existing_redirect:
                return existing_redirect.new_path
            raise Http404()


class _CharacterViewMixin:
    def dispatch(self, *args, **kwargs):
        """Record a StaticAssetView before returning the response."""
        response = super().dispatch(*args, **kwargs)
        StaticAssetView.create_from_request(self.request, self.object.static_asset_id)
        return response


class CharacterVersionDetail(_CharacterViewMixin, DetailView):
    """Display a character version."""

    model = CharacterVersion
    context_object_name = 'character_version'

    def get_object(self, queryset: Optional[models.query.QuerySet] = ...) -> CharacterVersion:
        """Get character version of the given slug and number."""
        filter_published = (
            {'is_published': True, 'character__is_published': True}
            if not self.request.user.is_staff and not self.request.user.is_superuser
            else {}
        )
        try:
            character_version = get_character_version(
                character__slug=self.kwargs['slug'],
                number=self.kwargs['number'],
                **filter_published,
            )
        except CharacterVersion.DoesNotExist:
            raise Http404()
        # Assign 'liked' attribute
        if self.request.user.is_authenticated:
            character_version.character.liked = character_version.character.likes.filter(
                user_id=self.request.user.pk
            ).exists()
        return character_version

    def get_context_data(self, **kwargs):
        """Add comments to the template context."""
        context = super().get_context_data(**kwargs)
        character_version = self.object
        context['character'] = character_version.character
        # Display edit buttons for editors/authors
        context[
            'user_can_edit_character'
        ] = self.request.user.is_staff and self.request.user.has_perm('character.change_character')

        # Comment threads
        comments: List[Comment] = get_annotated_comments(character_version, self.request.user.pk)
        context['comments'] = comments_to_template_type(
            comments, character_version.comment_url, self.request.user
        )

        return context


class CharacterShowcaseDetail(_CharacterViewMixin, DetailView):
    """Display a character showcase."""

    model = CharacterShowcase
    context_object_name = 'character_showcase'

    def get_object(self, queryset: Optional[models.query.QuerySet] = ...) -> CharacterShowcase:
        """Get character version of the given slug and number."""
        try:
            showcase = get_character_showcase(slug=self.kwargs['slug'], pk=self.kwargs['pk'])
        except CharacterShowcase.DoesNotExist:
            raise Http404()
        return showcase

    def get_context_data(self, **kwargs):
        """Add comments to the template context."""
        context = super().get_context_data(**kwargs)
        showcase = self.object
        # Display edit buttons for editors/authors
        context[
            'user_can_edit_character'
        ] = self.request.user.is_staff and self.request.user.has_perm('character.change_character')

        # Comment threads
        comments: List[Comment] = get_annotated_comments(showcase, self.request.user.pk)
        context['comments'] = comments_to_template_type(
            comments, showcase.comment_url, self.request.user
        )

        return context
