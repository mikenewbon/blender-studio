from actstream.models import Action
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from blog.models import Post
from comments.models import Comment
from common.tests.factories.blog import PostFactory
from common.tests.factories.comments import CommentUnderPostFactory
from common.tests.factories.films import FilmFactory
from common.tests.factories.helpers import create_test_image
from common.tests.factories.users import UserFactory

User = get_user_model()


class TestPostCreation(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = User.objects.create_superuser(
            username='superuser', password='Blender123!', email='admin@example.com'
        )
        cls.film = FilmFactory()
        cls.thumbnail = create_test_image()
        cls.post_add_url = reverse('admin:blog_post_add')

    def setUp(self) -> None:
        self.client.login(username='superuser', password='Blender123!')

    def test_post_creation(self):
        initial_post_count = Post.objects.count()

        with self.thumbnail as img:
            post_form_data = {
                'film': self.film.id,
                'title': 'New blog post',
                'slug': 'new-blog-post',
                'topic': 'Announcement',
                'content': '# Test text',
                'thumbnail': img,
                'author': self.admin.id,
            }
            response = self.client.post(self.post_add_url, post_form_data, follow=True)
            self.assertEqual(response.status_code, 200)

        self.assertEqual(Post.objects.count(), initial_post_count + 1)
        post = Post.objects.latest('date_created')
        self.assertHTMLEqual(post.content_html, '<h1>Test text</h1>')

    def test_updating_post(self):
        post = PostFactory()
        initial_post_count = Post.objects.count()

        post_change_url = reverse('admin:blog_post_change', kwargs={'object_id': post.pk})
        change_data = {
            'title': post.title,
            'category': post.category,
            'content': 'Updated content with *markdown*',
        }
        response = self.client.post(post_change_url, change_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), initial_post_count)

    def test_blog_author_cannot_be_deleted(self):
        post = PostFactory()

        self.assertFalse(post.author.is_staff)
        self.assertFalse(post.author.is_superuser)
        self.assertFalse(post.author.can_be_deleted)


class TestPostComments(TestCase):
    def setUp(self):
        self.user_without_subscription = UserFactory()
        self.user = UserFactory()
        self.other_user = UserFactory()

        self.post = PostFactory()
        self.post_url = reverse('api-post-comment', kwargs={'post_pk': self.post.pk})
        self.post_comment = CommentUnderPostFactory(comment_post__post=self.post)

        # Commenting without subscription is not allowed, so add these to the right group
        subscribers, _ = Group.objects.get_or_create(name='subscriber')
        self.user.groups.add(subscribers)
        self.other_user.groups.add(subscribers)
        self.post_comment.user.groups.add(subscribers)

    def test_reply_to_comment_creates_notifications(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        data = {'message': 'Comment message', 'reply_to': self.post_comment.pk}
        response = self.client.post(self.post_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 2)

        # No notifications for the user who replied to the comment
        self.assertEqual(list(Action.objects.notifications(self.user)), [], self.user)
        # A notification for the author of the comment they replied to
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.post_comment.user)],
            [f'{self.user} replied to {self.post_comment} on {self.post} 0 minutes ago'],
            self.post_comment.user,
        )
        # A notification for the author of the blog post
        comment = Comment.objects.get(pk=response.json()['id'])
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.post.author)],
            [f'{self.user} commented {comment} on {self.post} 0 minutes ago'],
        )

    def test_reply_to_your_own_comment_does_not_create_notification(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.post_comment.user)
        data = {'message': 'Comment message', 'reply_to': self.post_comment.pk}
        response = self.client.post(self.post_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)

        comment = Comment.objects.get(pk=response.json()['id'])
        # No notifications for the user who replied to the comment
        self.assertEqual(list(Action.objects.notifications(self.post_comment.user)), [])
        # A notification for the author of the blog post
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.post.author)],
            [f'{self.post_comment.user} commented {comment} on {self.post} 0 minutes ago'],
        )

    def test_liking_post_comment_creates_notification_for_comments_author(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        response = self.client.post(
            self.post_comment.like_url, {'like': True}, content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)
        action = Action.objects.first()
        self.assertEqual(action.action_object, self.post_comment)
        self.assertEqual(action.actor, self.user)
        self.assertEqual(action.target, self.post)
        self.assertFalse(action.public)

        self.assertNotEqual(self.post.author, self.post_comment.user)
        # Comment's author should be notified about the like on their comment
        self.assertEqual(
            [str(_) for _ in Action.objects.notifications(self.post_comment.user)],
            [f'{self.user} liked {self.post_comment} on {self.post} 0 minutes ago'],
        )
        # but blog post's author should not be notified
        self.assertEqual(list(Action.objects.notifications(self.post.author)), [], self.post.author)

    def test_commenting_on_post_creates_notification_for_posts_author(self):
        # No activity yet
        self.assertEqual(Action.objects.count(), 0)

        self.client.force_login(self.user)
        data = {'message': 'Comment message'}
        response = self.client.post(self.post_url, data, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Action.objects.count(), 1)
        action = Action.objects.first()
        comment = Comment.objects.get(pk=response.json()['id'])
        self.assertEqual(action.actor, self.user)
        self.assertEqual(action.target, self.post)
        self.assertEqual(action.action_object, comment)
        self.assertEqual(
            str(action),
            f'{self.user} commented {comment} on {self.post} 0 minutes ago',
            str(action),
        )

        self.assertNotEqual(self.post.author, self.post_comment.user)
        # Blog post's author should be notified about the comment on their post
        self.assertEqual(list(Action.objects.notifications(self.post.author)), [action])
        self.assertEqual(list(Action.objects.notifications(self.post_comment.user)), [])
