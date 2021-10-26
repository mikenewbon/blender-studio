import datetime
import mimetypes
import pytz
import pathlib
import tempfile
from typing import Optional
from bson import ObjectId
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from blender_id_oauth_client.models import OAuthUserInfo
from cloud_import.management import mongo
import static_assets.models as models_static_assets
import comments.models as models_comments
from cloud_import.management import files
import films.models as models_films

User = get_user_model()


class ImportCommand(BaseCommand):
    def _localize_date(self, date):
        return pytz.utc.localize(date)

    def console_log(self, message: str):
        """Utility to print NOTICE stdout messages."""
        self.stdout.write(self.style.NOTICE(message))

    def get_or_create_user(self, user_object_id: ObjectId) -> (User, bool):
        user_doc = mongo.users_collection.find_one({'_id': ObjectId(user_object_id)})
        try:
            oauth = OAuthUserInfo.objects.get(oauth_user_id=user_doc['auth'][0]['user_id'])
            user = oauth.user
            self.console_log(f"Fetched user {user.username}")
            is_created = False
        except OAuthUserInfo.DoesNotExist:
            return None, False
        except TypeError:
            return None, False
        except User.DoesNotExist:
            return None, False
        return user, is_created

    def reconcile_user_view_progress(self, user, user_doc):
        if 'nodes' not in user_doc or 'view_progress' not in user_doc['nodes']:
            return
        for node_id, values in user_doc['nodes']['view_progress'].items():
            node = mongo.nodes_collection.find_one({'_id': ObjectId(node_id)})

            try:
                static_asset = models_static_assets.StaticAsset.objects.get(
                    slug=str(node['properties']['file'])
                )
                self.console_log(
                    f"Found asset_id {static_asset.id} for {node['properties']['file']}"
                )
            except models_static_assets.StaticAsset.DoesNotExist:
                file_doc = mongo.files_collection.find_one(
                    {'_id': ObjectId(node['properties']['file'])}
                )
                if 'picture' in node:
                    thumbnail_file_doc = mongo.files_collection.find_one(
                        {'_id': ObjectId(node['picture'])}
                    )
                else:
                    thumbnail_file_doc = None

                self.console_log(f"Create asset_id asset for {node['properties']['file']}")

                static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc)

            if static_asset.source_type != 'video':
                self.console_log(f"File {static_asset.original_filename} is not a video, skipping")
                continue

            try:
                static_asset.video
            except models_static_assets.Video.DoesNotExist:
                self.console_log(f"File {static_asset.original_filename} does not exist, skipping")
                continue

            # Get or create video progress
            try:
                progress = models_static_assets.UserVideoProgress.objects.get(
                    user=user, video=static_asset.video
                )
            except models_static_assets.UserVideoProgress.DoesNotExist:
                progress = models_static_assets.UserVideoProgress.objects.create(
                    user=user,
                    video=static_asset.video,
                    position=datetime.timedelta(seconds=values['progress_in_sec']),
                )
            progress.date_created = pytz.utc.localize(values['last_watched'])
            progress.date_updated = pytz.utc.localize(values['last_watched'])
            progress.save()

    def reconcile_user(self, user, user_doc):
        self.console_log(f"\tReconciling user {user_doc['username']}")
        user.date_joined = pytz.utc.localize(user_doc['_created'])
        user.save()
        user.full_name = user_doc['full_name']
        if 'settings' in user_doc and 'email_communications' in user_doc['settings']:
            if user_doc['settings']['email_communications'] == 1:
                user.is_subscribed_to_newsletter = True
        user.save()

        if 'auth' in user_doc and user_doc['auth']:
            OAuthUserInfo.objects.get_or_create(
                user=user, oauth_user_id=user_doc['auth'][0]['user_id']
            )

    def reconcile_comment_ratings(self, comment_doc):
        if 'ratings' not in comment_doc['properties']:
            return

        comment = self.get_or_create_comment(comment_doc)
        for rating in comment_doc['properties']['ratings']:
            user, _ = self.get_or_create_user(rating['user'])
            self.console_log(f"Updating ratings for comment {comment.id}")
            models_comments.Like.objects.get_or_create(comment=comment, user=user)

    def get_or_create_comment(self, comment_doc, parent_comment_doc=None):
        try:
            comment = models_comments.Comment.objects.get(slug=str(comment_doc['_id']))
        except models_comments.Comment.DoesNotExist:
            # Get the comment author
            user, _ = self.get_or_create_user(comment_doc['user'])
            comment = models_comments.Comment.objects.create(
                message=comment_doc['properties']['content'],
                user=user,
                slug=str(comment_doc['_id']),
            )
        # Force reconcile dates and content
        comment.date_created = pytz.utc.localize(comment_doc['_created'])
        comment.date_updated = pytz.utc.localize(comment_doc['_updated'])
        # Legacy comments were converted under content_html
        if 'content_html' in comment_doc['properties']:
            comment.message_html = comment_doc['properties']['content_html']
        # Newer comments are available under _content_html
        if '_content_html' in comment_doc['properties']:
            comment.message_html = comment_doc['properties']['_content_html']
        comment.save()

        if parent_comment_doc:
            self.console_log("Setting parent to comment")
            parent_comment = self.get_or_create_comment(parent_comment_doc)
            comment.reply_to = parent_comment
            comment.save()
        return comment

    def reconcile_file_field(
        self, file_uuid, instance, attr_name, variation_subdoc=None, force=False
    ):
        """Download file from cloud storage and upload to S3."""
        file_doc = mongo.files_collection.find_one({'_id': ObjectId(file_uuid)})
        if not file_doc:
            self.console_log(f"\tFile {file_uuid} does not exist, skipping")
            return
        file_path = (
            file_doc.get('file_path') if not variation_subdoc else variation_subdoc.get('file_path')
        )
        if not file_path:
            self.console_log(f'No file_path for {file_doc} or {variation_subdoc}')
            return

        source = getattr(instance, attr_name)
        if source and not force:
            # If no variation is detected, do not reconcile
            if '-' not in source.name:
                self.console_log(f"\tSkipping existing file {file_uuid} {source.name}")
                return

        self.console_log(f"\tProcessing file {file_uuid} {source.name}")
        with tempfile.TemporaryDirectory() as tmp_dirname:
            self.console_log(f"\tCreated temporary directory {tmp_dirname}")
            tmp_path = pathlib.Path(tmp_dirname)
            dest_file_path_s3 = files.generate_s3_path(file_path)
            setattr(instance, attr_name, dest_file_path_s3)

            # Check if file is already on S3
            if files.file_on_s3(
                files.s3_client,
                settings.AWS_STORAGE_BUCKET_NAME,
                dest_file_path_s3,
            ):
                print(f"File {dest_file_path_s3} already exists on S3, skipping upload")
                instance.save()
                return

            # Collect storage metadata
            guessed_content_type, _ = mimetypes.guess_type(dest_file_path_s3)
            content_type = getattr(instance, 'content_type', guessed_content_type)
            content_disposition = getattr(instance, 'content_disposition', None)

            # Download file
            downloaded_file_path: Optional[pathlib.Path] = files.download_file_from_storage(
                file_doc, tmp_path, variation_subdoc
            )
            # Set value on instance
            if not downloaded_file_path:
                self.console_log(f"\tSkipping non existing file {file_uuid}")
                return

            # Upload to S3
            files.upload_file_to_s3(
                str(downloaded_file_path),
                dest_file_path_s3,
                ContentType=content_type,
                ContentDisposition=content_disposition,
            )
            instance.save()

    def reconcile_static_asset_video(
        self, file_doc, static_asset: models_static_assets.StaticAsset
    ):
        self.console_log(f"\tReconciling Video properties for asset {static_asset.id}")
        try:
            video = models_static_assets.Video.objects.get(static_asset=static_asset)
        except models_static_assets.Video.DoesNotExist:
            video = models_static_assets.Video.objects.create(
                static_asset=static_asset, duration=datetime.timedelta(seconds=10)
            )

        if file_doc.get('variations') and 'duration' in file_doc['variations'][0]:
            video.duration = datetime.timedelta(seconds=file_doc['variations'][0]['duration'])
        if 'size' in file_doc:
            video.resolution_label = file_doc['size']
        if 'height' in file_doc:
            video.height = file_doc['height']
        if 'width' in file_doc:
            video.width = file_doc['width']
        video.save()

    def reconcile_static_asset_image(
        self, file_doc, static_asset: models_static_assets.StaticAsset
    ):
        self.console_log(f"\tReconciling Image properties for {static_asset.id}")
        try:
            image = models_static_assets.Image.objects.get(static_asset=static_asset)
        except models_static_assets.Image.DoesNotExist:
            image = models_static_assets.Image.objects.create(static_asset=static_asset)

        if 'height' in file_doc:
            image.height = file_doc['height']
        if 'width' in file_doc:
            image.width = file_doc['width']
        image.save()

    def reconcile_static_asset(
        self, file_doc, static_asset: models_static_assets.StaticAsset, thumbnail_file_doc=None
    ):
        self.console_log(f"Reconciling file {file_doc['_id']} {file_doc.get('file_path')}")
        # Update properties
        static_asset.slug = str(file_doc['_id'])
        # Update original_filename
        static_asset.original_filename = file_doc['filename']
        # Update filesize
        static_asset.size_bytes = file_doc['length']
        # Update date_created
        static_asset.date_created = pytz.utc.localize(file_doc['_created'])
        static_asset.date_updated = pytz.utc.localize(file_doc['_updated'])
        # Update content_type
        static_asset.content_type = file_doc['content_type']
        static_asset.user, _ = self.get_or_create_user(file_doc['user'])
        static_asset.save()

        self.reconcile_file_field(file_doc['_id'], static_asset, 'source')
        if thumbnail_file_doc:
            self.reconcile_file_field(thumbnail_file_doc['_id'], static_asset, 'thumbnail')

        if static_asset.source_type == 'video':
            self.reconcile_static_asset_video(file_doc, static_asset)

        if static_asset.source_type == 'image':
            self.reconcile_static_asset_image(file_doc, static_asset)

    def reconcile_film_asset(self, asset_doc, collection: models_films.Collection):
        if not (asset_doc.get('properties') or {}).get('file'):
            if not asset_doc.get('_deleted'):
                self.console_log(f'No file available in {asset_doc}')
            return
        asset_slug = str(asset_doc['_id'])
        self.console_log(f"Processing asset with {asset_slug}")
        try:
            asset = models_films.Asset.objects.get(slug=asset_slug)
        except models_films.Asset.DoesNotExist:
            if 'description' not in asset_doc:
                self.console_log(f'Missing description on {asset_doc}')
            description = asset_doc.get('description', '')
            asset = models_films.Asset.objects.create(
                date_created=self._localize_date(asset_doc['_created']),
                date_updated=self._localize_date(asset_doc['_updated']),
                slug=asset_slug,
                film=collection.film,
                collection=collection,
                description=description,
                category='artwork',
                is_published=True,
            )

        # Set Production File category if asset is of type file and file is an image
        if (
            'content_type' in asset_doc['properties']
            and asset_doc['properties']['content_type'] == 'file'
        ):
            asset.category = 'production_file'

        # Set Tags
        if 'tags' in asset_doc['properties']:
            asset.tags.add(*asset_doc['properties']['tags'])

        # Assign static asset
        file_doc = mongo.files_collection.find_one(
            {'_id': ObjectId(asset_doc['properties']['file'])}
        )
        if not file_doc:
            self.console_log(f'Missing file_doc for {asset_doc}')
            return
        if 'picture' in asset_doc:
            thumbnail_file_doc = mongo.files_collection.find_one(
                {'_id': ObjectId(asset_doc['picture'])}
            )
        else:
            thumbnail_file_doc = None
        asset.static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc)
        asset.save()

        self.reconcile_film_asset_comments(asset)

    def reconcile_film_asset_comments(self, asset: models_films.Asset):
        """Fetch comments."""
        comments = mongo.nodes_collection.find(
            {
                'node_type': 'comment',
                'parent': ObjectId(asset.slug),
                'properties.status': 'published',
                '_deleted': {'$ne': True},
            }
        )
        comments_count = 0
        for comment_doc in comments:
            self.console_log(f"Processing comment {comment_doc['_id']} for asset {asset.id}")
            comment = self.get_or_create_comment(comment_doc)
            models_films.AssetComment.objects.get_or_create(asset=asset, comment=comment)
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
                models_films.AssetComment.objects.get_or_create(asset=asset, comment=reply_comment)
                self.reconcile_comment_ratings(reply_comment_doc)

        if comments_count > 0:
            self.console_log(f"Processed {comments_count} comments")

    def get_or_create_static_asset(self, file_doc, thumbnail_file_doc=None):
        file_slug = str(file_doc['_id'])
        try:
            static_asset = models_static_assets.StaticAsset.objects.get(slug=file_slug)
        except models_static_assets.StaticAsset.DoesNotExist:
            content_type = file_doc['content_type'].split('/')[0]
            if content_type not in {'image', 'video'}:
                content_type = 'file'
            static_asset = models_static_assets.StaticAsset.objects.create(
                source_type=content_type,
                original_filename=file_doc.get('filename', file_doc['name']),
                size_bytes=file_doc['length'],
                user_id=1,
                slug=file_slug,
            )

        self.reconcile_static_asset(file_doc, static_asset, thumbnail_file_doc)

        if 'video' in file_doc['content_type'] and 'variations' in file_doc:
            for v in file_doc['variations']:
                file_path = v.get('file_path')
                self.console_log(f"\tProcessing variation {file_path}")
                if file_path and file_path.endswith('.webm'):
                    self.console_log("\tSkipping .webm variation")
                    continue
                variation, _ = models_static_assets.VideoVariation.objects.get_or_create(
                    video=static_asset.video,
                    resolution_label=v['size'],
                    size_bytes=v['length'],
                    height=v['height'],
                    width=v['width'],
                    content_type=v['content_type'],
                )

                self.reconcile_file_field(file_doc['_id'], variation, 'source', variation_subdoc=v)

        models_static_assets.StaticAsset.objects.filter(
            slug=static_asset.slug, id=static_asset.pk
        ).update(
            date_created=pytz.utc.localize(file_doc['_created']),
            date_updated=pytz.utc.localize(file_doc['_updated']),
        )
        static_asset.refresh_from_db()
        return static_asset

    def get_or_create_collection(self, collection_doc, film):
        collection_slug = str(collection_doc['_id'])

        try:
            self.console_log(f"Getting collection {collection_slug}")
            collection = models_films.Collection.objects.get(slug=collection_slug)
        except models_films.Collection.DoesNotExist:
            self.console_log(f"Not found, creating collection {collection_slug}")
            collection = models_films.Collection.objects.create(
                order=1, film=film, name=collection_doc['name'], slug=collection_slug
            )
        if 'order' in collection_doc['properties']:
            collection.order = collection_doc['properties']['order']

        if 'description' in collection_doc:
            collection.text = collection_doc['description']

        collection.date_created = pytz.utc.localize(collection_doc['_created'])
        collection.date_updated = pytz.utc.localize(collection_doc['_updated'])
        collection.user, _ = self.get_or_create_user(collection_doc['user'])
        collection.save()

        # Ensure media
        if 'picture' in collection_doc and collection_doc['picture']:
            self.reconcile_file_field(collection_doc['picture'], collection, 'thumbnail')

        # Traverse parent
        if 'parent' in collection_doc and collection_doc['parent']:
            parent_collection_doc = mongo.nodes_collection.find_one(
                {'_id': ObjectId(collection_doc['parent'])}
            )
            if parent_collection_doc:
                collection.parent = self.get_or_create_collection(parent_collection_doc, film)
                collection.save()
            else:
                self.console_log(f"Parent collection {collection_doc['parent']} not found")

        return collection
