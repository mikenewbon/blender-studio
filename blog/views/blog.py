from typing import List

from django.http.request import HttpRequest
from django.http.response import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_safe

from blog.models import Post, Revision
from blog.queries import get_latest_post_revisions
from comments.models import Comment
from comments.queries import get_annotated_comments
from comments.views.common import comments_to_template_type


@require_safe
def post_list(request: HttpRequest) -> HttpResponse:
    """
    Renders a list of published :model:`blog.Revision`-s (i.e. latest post versions).

    **Context**
        ``posts``
            The list of published posts' latest revisions, ordered by date_created descending.
            Each post revision is annotated with the following additional attributes:

            - ``slug`` - str, the post slug,
            - ``is_new`` - a bool, whether the post was created in the last 7 days.
        ``user_can_edit_post``
            A bool specifying whether the current user should be able to edit
            :model:`blog.Post`-s displayed in the page.

    **Template**
        :template:`blog/posts.html`
    """
    context = {
        'posts': get_latest_post_revisions(),
        'user_can_edit_post': (request.user.is_staff and request.user.has_perm('blog.change_post')),
    }

    return render(request, 'blog/posts.html', context)


@require_safe
def post_detail(request: HttpRequest, post_slug: str) -> HttpResponse:
    """
    Renders a single published :model:`blog.Post` page, containing its latest published revision.

    **Context**
        ``post``
            A :model:`blog.Revision` instance. The latest published revision of the post.
            (It is named ``post`` for consistency in the templates - see the
            :view:`blog.views.blog.post_list`.)
        ``post_author``
            A str, author's full name (may be empty if the user has no first and last name set).
        ``post_date_created``
            A datetime, creation date of the entire post (not the latest revision).
        ``user_can_edit_post``
            A bool specifying whether the current user has permission to edit :model:`blog.Post`.
        ``comments``
            A ``typed_templates.Comments`` instance with post comments.

    **Template**
        :template:`blog/post_detail.html`
    """
    post = get_object_or_404(Post, slug=post_slug, is_published=True)
    try:
        latest_revision: Revision = post.revisions.filter(is_published=True).latest('date_created')
    except Revision.DoesNotExist:
        raise Http404('No revision matches the given query.')

    comments: List[Comment] = get_annotated_comments(post, request.user.pk)

    context = {
        'post': latest_revision,
        'post_author_profile': post.author.profile,
        'post_date_created': post.date_created,
        'user_can_edit_post': (request.user.is_staff and request.user.has_perm('blog.change_post')),
        'comments': comments_to_template_type(comments, post.comment_url, request.user),
    }

    return render(request, 'blog/post_detail.html', context)
