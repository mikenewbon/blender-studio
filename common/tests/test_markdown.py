from django.test import TestCase

from common.markdown import render as render_markdown


class RenderMarkdownTest(TestCase):
    def test_attachment_full_paragraph_link_is_not_urlised(self):
        text = '{attachment 123 link="http://example.com"}'
        self.assertEqual(f'<p>{text}</p>\n', str(render_markdown(text)))

    def test_attachment_part_of_a_paragraph_link_is_not_urlised(self):
        text = 'blah blah {attachment 123 link="http://example.com"} more blah blah'
        self.assertEqual(f'<p>{text}</p>\n', str(render_markdown(text)))

    def test_iframe_full_paragraph_src_is_not_urlised(self):
        text = '{iframe src="http://example.com"}'
        self.assertEqual(f'<p>{text}</p>\n', str(render_markdown(text)))

    def test_iframe_part_of_a_paragraph_src_is_not_urlised(self):
        text = 'blah blah {iframe src=http://example.com} more blah blah'
        self.assertEqual(f'<p>{text}</p>\n', str(render_markdown(text)))

    def test_linkify_urlize_a_link(self):
        text = '**bold** https://example.com'
        self.assertEqual(
            '<p><strong>bold</strong> '
            '<a href="https://example.com">https://example.com</a></p>\n',
            str(render_markdown(text)),
        )
