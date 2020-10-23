import pytz
from bson import ObjectId

from cloud_import.management import mongo
from cloud_import.management.mixins import ImportCommand
import blog.models as models_blog
import training.models as models_training


class Command(ImportCommand):
    help = 'Augment training assets with extra info'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slug', dest='slugs', action='append', help="provides training slugs"
        )

        parser.add_argument(
            '--all', action='store_true', help='Reconcile all trainings',
        )

    def assign_user(self, asset, node_doc):

        user, _ = self.get_or_create_user(node_doc['user'])
        self.console_log(f"Assign user {user.username} to asset {asset.id} - {asset.name}")

        asset.static_asset.user = user
        asset.static_asset.save()
        self.console_log(f"\tUpdated static_asset {asset.static_asset.id}")

    def reconcile_post_comments(self, post: models_blog.Post):
        if not post.legacy_id:
            return
        # Fetch comments
        comments = mongo.nodes_collection.find(
            {
                'node_type': 'comment',
                'parent': ObjectId(post.legacy_id),
                'properties.status': 'published',
                '_deleted': {'$ne': True},
            }
        )
        comments_count = 0
        for comment_doc in comments:
            self.console_log(f"Processing comment {comment_doc['_id']} for asset {post.id}")
            comment = self.get_or_create_comment(comment_doc)
            models_blog.PostComment.objects.get_or_create(post=post, comment=comment)
            self.reconcile_comment_ratings(comment_doc)
            response_comments = mongo.nodes_collection.find(
                {
                    'node_type': 'comment',
                    'parent': comment_doc['_id'],
                    'properties.status': 'published',
                    '_deleted': {'$ne': True},
                }
            )
            comments_count += 1

            for reply_comment_doc in response_comments:
                reply_comment = self.get_or_create_comment(reply_comment_doc, comment_doc)
                models_blog.PostComment.objects.get_or_create(post=post, comment=reply_comment)
                self.reconcile_comment_ratings(reply_comment_doc)

        if comments_count > 0:
            self.console_log(f"Processed {comments_count} comments")

    def reconcile_post_attachments(self, post_doc, post: models_blog.Post):
        self.console_log(f"Reconciling attachments for post_doc {post_doc['_id']}")
        if 'properties' not in post_doc:
            return
        if 'attachments' not in post_doc['properties']:
            self.console_log("Post has no attachments")
            return
        for slug, attachment in post_doc['properties']['attachments'].items():
            # Replace the "{attachment <slug>" string with "{attachment <static_asset_id>"
            if 'oid' not in attachment:
                continue
            file_doc = mongo.files_collection.find_one({'_id': ObjectId(attachment['oid'])})
            if not file_doc:
                continue
            static_asset = self.get_or_create_static_asset(file_doc)
            post.attachments.add(static_asset)
            revision = post.revisions.first()
            str_src = f"{{attachment {slug}"
            str_dst = f"{{attachment {static_asset.pk}"
            revision.content = revision.content.replace(str_src, str_dst)
            revision.html_content = revision.html_content.replace(str_src, str_dst)
            revision.save()

    def reconcile_blog(self, training):
        project = mongo.projects_collection.find_one({'url': training.slug})

        cloud_posts = mongo.nodes_collection.find(
            {
                'node_type': 'post',
                '_deleted': {'$ne': True},
                'project': project['_id'],
                'properties.status': 'published',
            }
        )
        for post_doc in cloud_posts:
            user, _ = self.get_or_create_user(post_doc['user'])
            slug = f"{training.slug}-{post_doc['properties']['url']}"
            try:
                post = models_blog.Post.objects.get(slug=slug)
            except models_blog.Post.DoesNotExist:
                post = models_blog.Post.objects.create(
                    slug=slug, author=user, is_published=True, legacy_id=str(post_doc['_id']),
                )
            models_blog.Post.objects.filter(pk=post.pk).update(
                date_updated=pytz.utc.localize(post_doc['_updated']),
                date_published=pytz.utc.localize(post_doc['_created']),
                date_created=pytz.utc.localize(post_doc['_created']),
            )
            post = models_blog.Post.objects.get(pk=post.pk)
            post.save()
            self.console_log(f"Retrieved post for {post_doc['_id']} with id {post.id}")

            try:
                revision = models_blog.Revision.objects.get(post=post)
            except models_blog.Revision.DoesNotExist:
                revision = models_blog.Revision.objects.create(
                    post=post,
                    editor=user,
                    title=post_doc['name'],
                    content=post_doc['properties']['content'],
                    is_published=True,
                )

            self.console_log(f"Retrieved revision {revision}")
            models_blog.Revision.objects.filter(pk=revision.pk).update(
                date_updated=pytz.utc.localize(post_doc['_updated']),
                date_created=pytz.utc.localize(post_doc['_created']),
            )
            revision = models_blog.Revision.objects.get(pk=revision.pk)
            revision.save()

            if 'picture' in post_doc and post_doc['picture']:
                self.reconcile_file_field(
                    post_doc['picture'], revision, 'header',
                )
                self.reconcile_file_field(
                    post_doc['picture'], revision, 'thumbnail',
                )

            # Get comments
            self.reconcile_post_comments(post)
            # Get attachments
            self.reconcile_post_attachments(post_doc, post)

    def handle(self, *args, **options):
        for training in models_training.Training.objects.all():
            self.reconcile_blog(training)
