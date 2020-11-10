from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import Post
from common.tests.factories.blog import PostFactory
from common.tests.factories.films import FilmFactory
from common.tests.factories.helpers import create_test_image


class TestPostAndRevisionCreation(TestCase):
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
