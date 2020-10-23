from typing import Any, List, Tuple

from django.contrib import admin, messages
from django.db.models.query import Prefetch, QuerySet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls.conf import path
from django.urls.resolvers import URLPattern
from django.utils.text import slugify

from blog.forms import PostChangeForm, PostAddForm
from blog.models import Post, Revision
from common.types import assert_cast


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    readonly_fields = ['date_created', 'date_updated', 'editor']
    list_display = ['__str__', 'post', 'topic', 'editor', 'is_published']
    list_filter = ['is_published', 'post']
    search_fields = ['title']
    save_as = True

    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        """Associate created object with the current user."""
        if not obj.pk:
            obj.editor = request.user
        super().save_model(request, obj, form, change)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        '__str__',
        'film',
        'author',
        'is_published',
        'is_last_revision_published',
        'date_updated',
    ]
    list_filter = [
        'is_published',
        'film',
    ]
    autocomplete_fields = ['author']
    search_fields = ['slug']

    def get_queryset(self, request: HttpRequest) -> 'QuerySet[Post]':
        queryset = super().get_queryset(request)
        return queryset.select_related('author', 'film').prefetch_related(
            Prefetch('revisions', queryset=Revision.objects.all(), to_attr='last_revision')
        )

    def last_revision_title(self, obj: Post) -> str:
        """Return the title of the latest created revision for the given post."""
        return assert_cast(str, getattr(obj, 'last_revision')[-1].title)

    def is_last_revision_published(self, obj: Post) -> bool:
        return assert_cast(bool, getattr(obj, 'last_revision')[-1].is_published)

    is_last_revision_published.boolean = True  # type: ignore[attr-defined]

    def get_urls(self) -> List[URLPattern]:
        urls = super().get_urls()
        revision_add_view_name = f'{self.model._meta.app_label}_{self.model._meta.model_name}_add'
        revision_change_view_name = (
            f'{self.model._meta.app_label}_{self.model._meta.model_name}_change'
        )
        custom_urls = [
            path(
                'add/', self.admin_site.admin_view(self.post_add_view), name=revision_add_view_name,
            ),
            path(
                '<path:object_id>/change/',
                self.admin_site.admin_view(self.post_change_view),
                name=revision_change_view_name,
            ),
        ]

        return custom_urls + urls

    def _set_post_and_revision_fields(
        self, post: Post, revision: Revision, request: HttpRequest
    ) -> Tuple[Post, Revision]:
        """
        Sets all the missing fields in the post and revision instances.

        Does not save the objects to the database.
        """
        if not post.slug:
            post.slug = slugify(revision.title)
        if not hasattr(post, 'author'):
            post.author = request.user

        if revision.is_published and not post.is_published:
            # If a post has no published revisions, it should not be published as well.
            # The first revision to be marked as published also sets the post's
            # `is_published` status to True.
            post.is_published = True

        revision.post = post
        revision.editor = request.user

        return post, revision

    def post_add_view(self, request: HttpRequest) -> HttpResponse:
        if request.method == 'POST':
            form = PostAddForm(request.POST, request.FILES)
            if form.is_valid():
                revision = form.save(commit=False)
                post = form.create_post()
                post, revision = self._set_post_and_revision_fields(post, revision, request=request)

                post.save()
                revision.save()

                message = f'The post “{revision.title}” was added successfully.'
                self.message_user(request, message, messages.SUCCESS)

                return redirect('admin:blog_post_changelist')
            else:
                form = PostAddForm(form.cleaned_data)
                return render(request, 'blog/admin_add_post.html', {'form': form})

        form = PostAddForm()
        return render(request, 'blog/admin_add_post.html', {'form': form})

    def post_change_view(self, request: HttpRequest, object_id: int) -> HttpResponse:
        post = get_object_or_404(Post, id=object_id)
        previous_revision = Revision.objects.filter(post=post).latest('date_created')

        if request.method == 'POST':
            form = PostChangeForm(request.POST, request.FILES)
            if form.is_valid():
                revision = form.save(commit=False)
                post, revision = self._set_post_and_revision_fields(post, revision, request=request)
                if not revision.thumbnail:
                    # It is not possible to set an initial value in a FileField, so we use
                    # the previous picture so as not to force the user to set it each time.
                    revision.thumbnail = previous_revision.thumbnail

                post.save()
                revision.save(force_insert=True)

                message = f'The post “{revision.title}” was changed successfully.'
                self.message_user(request, message, messages.SUCCESS)

                return redirect('admin:blog_post_changelist')
            else:
                form = PostChangeForm(form.cleaned_data)
                return render(request, 'blog/admin_change_post.html', {'form': form})

        form = PostChangeForm(instance=previous_revision)
        return render(request, 'blog/admin_change_post.html', {'form': form})
