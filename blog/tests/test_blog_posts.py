from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from blog.models import Post, Revision
from common.tests.factories.blog import RevisionFactory, PostFactory
from common.tests.factories.films import FilmFactory
from common.tests.factories.helpers import create_test_image


class TestPostAndRevisionCreation(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.admin = User.objects.create_superuser(
            username='superuser', password='Blender123!', email='admin@example.com'
        )
        cls.film = FilmFactory()
        cls.picture_16_9 = create_test_image()
        cls.post_add_url = reverse('admin:blog_post_add')

    def setUp(self) -> None:
        self.client.login(username='superuser', password='Blender123!')

    def test_post_creation(self):
        initial_post_count = Post.objects.count()
        initial_revision_count = Revision.objects.count()

        with self.picture_16_9 as img:
            post_form_data = {
                'film': self.film.id,
                'title': 'New blog post',
                'topic': 'Announcement',
                'content': '#Test text',
                'picture_16_9': img,
            }
            response = self.client.post(self.post_add_url, post_form_data, follow=True)
            self.assertEqual(response.status_code, 200)

        self.assertEqual(Post.objects.count(), initial_post_count + 1)
        self.assertEqual(Revision.objects.count(), initial_revision_count + 1)
        revision = Revision.objects.latest('date_created')
        self.assertHTMLEqual(revision.html_content, '<h1>Test text</h1>')

    def test_updating_post_creates_new_revision(self):
        post = PostFactory()
        revision = RevisionFactory(post=post)
        initial_post_count = Post.objects.count()
        initial_revision_count = Revision.objects.count()

        post_change_url = reverse('admin:blog_post_change', kwargs={'object_id': revision.post.pk})
        change_data = {
            'title': revision.title,
            'topic': revision.topic,
            'content': 'Updated content with *markdown*',
        }
        response = self.client.post(post_change_url, change_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), initial_post_count)
        self.assertEqual(Revision.objects.count(), initial_revision_count + 1)
        latest_revision = post.revisions.latest('date_created')
        self.assertEqual(latest_revision.content, change_data['content'])
