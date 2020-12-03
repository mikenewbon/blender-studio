from typing import List

from django.views.generic import ListView, DetailView
from django.db.models.query import QuerySet

from blog.models import Post, Like
from comments.models import Comment
from comments.queries import get_annotated_comments
from comments.views.common import comments_to_template_type


class PostList(ListView):
    model = Post
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self) -> QuerySet:
        return Post.objects.filter()


class PostDetail(DetailView):
    model = Post
    context_object_name = 'post'

    def get_object(self) -> Post:
        object_ = super().get_object()
        if self.request.user.is_authenticated:
            object_.liked = Like.objects.filter(
                post_id=object_.pk, user_id=self.request.user.pk
            ).exists()
        return object_

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post: Post = self.get_object()
        # Display edit buttons for editors/authors
        context['user_can_edit_post'] = self.request.user.is_staff and self.request.user.has_perm(
            'blog.change_post'
        )
        # Shorthand for Author profile
        context['post_author_profile'] = getattr(post.author, 'profile', None)

        # Comment threads
        comments: List[Comment] = get_annotated_comments(post, self.request.user.pk)
        context['comments'] = comments_to_template_type(
            comments, post.comment_url, self.request.user
        )

        return context
