from unittest.mock import ANY
import json

from django.test import TestCase
from django.urls import reverse

from common.tests.factories.comments import CommentFactory
from common.tests.factories.training import SectionFactory
from common.tests.factories.users import UserFactory


class TestCommentEndpoint(TestCase):
    maxDiff = None

    def setUp(self):
        self.user = UserFactory()
        self.section = SectionFactory()
        self.comment = CommentFactory(user=self.user)
        self.comment_url = reverse('section-comment', kwargs={'section_pk': self.section.pk})
        self.client.force_login(self.user)

    def test_comment_full_response(self):
        message = '# Header\n**bold** _italic_'
        response = self.client.post(
            self.comment_url,
            {'message': message, 'reply_to': None},
            content_type='application/json',
        )

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        comment_id = response_data['id']
        self.assertEqual(
            response_data,
            {
                'date_string': ANY,
                'delete_url': f'/comments/api/comments/{comment_id}/delete/',
                'edit_url': f'/comments/api/comments/{comment_id}/edit/',
                'full_name': '',
                'username': self.user.username,
                'id': comment_id,
                'like_url': f'/comments/api/comments/{comment_id}/like/',
                'liked': False,
                'likes': 0,
                'message': message,
                'message_html': '<h1>Header</h1>\n<p><strong>bold</strong> <em>italic</em></p>\n',
                'profile_image_url': ANY,
            },
        )

    def test_comment_with_shortcodes(self):
        message = '# Header\n**bold** _italic_ {youtube UbyxFZSZZ90}'
        response = self.client.post(
            self.comment_url,
            {'message': message, 'reply_to': None},
            content_type='application/json',
        )

        response_data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        comment_id = response_data['id']
        self.assertEqual(
            response_data,
            {
                'date_string': ANY,
                'delete_url': f'/comments/api/comments/{comment_id}/delete/',
                'edit_url': f'/comments/api/comments/{comment_id}/edit/',
                'full_name': '',
                'username': self.user.username,
                'id': comment_id,
                'like_url': f'/comments/api/comments/{comment_id}/like/',
                'liked': False,
                'likes': 0,
                'message': message,
                'message_html': '<h1>Header</h1>\n'
                '<p><strong>bold</strong> <em>italic</em> <div '
                'class="embed-responsive embed-responsive-16by9"><iframe '
                'class="shortcode youtube embed-responsive-item" width="560" '
                'height="315" '
                'src="https://www.youtube.com/embed/UbyxFZSZZ90?rel=0" '
                'frameborder="0" allow="autoplay; encrypted-media" '
                'allowfullscreen></iframe></div></p>\n',
                'profile_image_url': ANY,
            },
        )
