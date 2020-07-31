from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_safe

from blog.models import Post
from blog.queries import get_posts_with_latest_revision


@require_safe
def post_list(request: HttpRequest) -> HttpResponse:
    """
    Renders a published :model:`blog.Post` list, each post with its latest published revision.

    **Context**
        ``posts``
            The list of published posts, ordered by date_created descending.
            Each post is annotated with the following additional attributes:

            - ``title`` - str, the latest published revision title,
            - ``description`` - (optional) str, a short description of the revision,
            - ``html_content`` - the html_content of the latest published revision,
            - ``is_new`` - a bool, whether the post was created in the last 7 days.


    **Template**
        :template:`blog/posts.html`
    """
    return render(request, 'blog/posts.html', {'posts': get_posts_with_latest_revision()})


@require_safe
def post_detail(request: HttpRequest, post_slug: str) -> HttpResponse:
    """
    Renders a single published :model:`blog.Post` page, containing its latest published revision.

    **Context**
        ``post``
            A :model:`blog.Revision` instance. The latest published revision of the post.
            (It is named ``post`` for consistency in the templates - see the
            :view:`blog.views.blog.post_list`.)
        ``user_can_edit_post``
            A bool specifying whether the current user should be able to edit
            :model:`blog.Post`-s displayed in the page.

    **Template**
        :template:`blog/post_detail.html`
    """
    context = {
        'post': (
            get_object_or_404(Post, slug=post_slug, is_published=True)
            .revisions.filter(is_published=True)
            .latest('date_created')
        ),
        'user_can_edit_post': (request.user.is_staff and request.user.has_perm('blog.change_post')),
    }

    return render(request, 'blog/post_detail.html', context)
