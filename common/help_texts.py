# noqa: D100
import common.markdown

markdown = '''
<p>Format the content in <a href="https://commonmark.org/help/">Markdown</a>.</p>
<div>
    <p>
        To make images float left or right of the text, use the following:
    </p>
    <p>
        <code>
        {attachment StaticAssetID class='float-left'}
        </code>
    </p>
    <p>
        <code>
        {attachment StaticAssetID class='float-right'}
        </code>
    </p>
</div>
'''
allowed_tags = ', '.join(f'<{tag}>' for tag in common.markdown.ALLOWED_TAGS)
markdown_with_html = markdown + (
    f'<p title="{allowed_tags}">Some HTML tags are allowed&nbsp;'
    '<span class="help help-tooltip">ℹ</span>'
)
