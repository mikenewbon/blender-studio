# noqa: D
import pprint

from bson import ObjectId

from cloud_import.management.mixins import ImportCommand
from cloud_import.management import mongo
from comments.models import Comment


class Command(ImportCommand):  # noqa: D
    help = 'Recover missing comment attachments.'

    def handle(self, *args, **options):  # noqa: D
        comments = Comment.objects.filter(message__contains='{attachment')
        self.console_log(f'Found {comments.count()} comments with attachments')
        for comment in comments:
            comment_node = list(
                mongo.nodes_collection.find(
                    {
                        'node_type': 'comment',
                        '_id': ObjectId(comment.slug),
                    }
                )
            )
            assert len(comment_node) == 1, f'Unexpected number of nodes found: {len(comment_node)}'
            comment_node = comment_node[0]

            attachments = comment_node.get('properties', {}).get('attachments', {})
            if not any(
                name in comment.message or name in comment.message_html for name in attachments
            ):
                self.console_log(f'{comment} already fixed, skipping')
                continue
            print(pprint.pprint(comment_node))
            attachment_name_to_id = {}
            for attachment_name, attachment in attachments.items():
                file_doc = mongo.files_collection.find_one({'_id': attachment['oid']})
                if not file_doc:
                    self.console_log(f'Missing doc for {attachment_name}, {attachment}')
                    continue
                asset = self.get_or_create_static_asset(file_doc)
                # print(asset, asset.date_created, asset.date_updated)
                attachment_name_to_id.update({attachment_name: asset.pk})
                # pprint.pprint(file_doc)
            # pprint.pprint(attachment_name_to_id)
            print('Changing: ', comment.message, comment.message_html)
            if not attachment_name_to_id:
                continue
            for name, pk in attachment_name_to_id.items():
                replacement = f'{{attachment {name}', f'{{attachment {pk}'
                comment.message = comment.message.replace(*replacement)
                comment.message_html = comment.message_html.replace(*replacement)
            print('      to: ', comment.message, comment.message_html)
            Comment.objects.filter(pk=comment.pk).update(
                message=comment.message,
                message_html=comment.message_html,
                date_updated=comment.date_updated,
            )
