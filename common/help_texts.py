# noqa: D100
import logging

from django.db.models import Q

import common.markdown

logger = logging.getLogger(__name__)

markdown = '''
<p>Format the content in <a href="https://commonmark.org/help/">Markdown</a>.</p>
<div>
    <p>
        To make images float left or right of the text, use the following:
    </p>
    <p>
        <code>
        {attachment StaticAssetID class='float-start'}
        </code>
    </p>
    <p>
        <code>
        {attachment StaticAssetID class='float-end'}
        </code>
    </p>
</div>
'''
allowed_tags = ', '.join(f'<{tag}>' for tag in common.markdown.ALLOWED_TAGS)
markdown_with_html = markdown + (
    f'<p title="{allowed_tags}">Some HTML tags are allowed&nbsp;'
    '<span class="help help-tooltip">ℹ</span>'
)


def _replace_float_classes_bs5(app_name, model_name, field_name):
    def _func(apps, schema_editor):
        model = apps.get_model(app_name, model_name)
        to_update = []
        filter_args = Q(**{f'{field_name}__contains': 'float-left'}) | Q(
            **{f'{field_name}__contains': 'float-right'}
        )
        for obj in model.objects.filter(filter_args):
            for _from, _to in (('float-left', 'float-start'), ('float-right', 'float-end')):
                setattr(obj, field_name, getattr(obj, field_name).replace(_from, _to))
            to_update.append(obj)
        if not to_update:
            return
        logger.warning(
            'Replacing float classes in %s "%s" of %s entries',
            len(to_update),
            field_name,
            model,
        )
        model.objects.bulk_update(to_update, fields={field_name, 'date_updated'})

    return _func


def _replace_float_classes_bs4(app_name, model_name, field_name):
    def _func(apps, schema_editor):
        model = apps.get_model(app_name, model_name)
        to_update = []
        filter_args = Q(**{f'{field_name}__contains': 'float-start'}) | Q(
            **{f'{field_name}__contains': 'float-end'}
        )
        for obj in model.objects.filter(filter_args):
            for _from, _to in (('float-start', 'float-left'), ('float-end', 'float-right')):
                setattr(obj, field_name, getattr(obj, field_name).replace(_from, _to))
            to_update.append(obj)
        if not to_update:
            return
        logger.warning(
            'Replacing float classes in %s "%s" of %s entries',
            len(to_update),
            field_name,
            model,
        )
        model.objects.bulk_update(to_update, fields={field_name, 'date_updated'})

    return _func
