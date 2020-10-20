import datetime
import pytz
import pathlib
import tempfile
from typing import Optional
from bson import ObjectId
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management.base import BaseCommand
from blender_id_oauth_client.models import OAuthUserInfo
from cloud_import.management import mongo
import static_assets.models as models_static_assets
import comments.models as models_comments
from cloud_import.management import files


class ImportCommand(BaseCommand):
    def console_log(self, message: str):
        """Utility to print NOTICE stdout messages."""
        self.stdout.write(self.style.NOTICE(message))

    def get_or_create_user(self, user_object_id: ObjectId) -> User:
        user_doc = mongo.users_collection.find_one({'_id': ObjectId(user_object_id)})
        try:
            user = User.objects.get(username=user_doc['username'])
            self.console_log(f"Fetched user {user.username}")
        except User.DoesNotExist:
            user = User.objects.create(username=user_doc['username'], email=user_doc['email'])
            self.console_log(f"Created user {user.username}")
        self.reconcile_user(user, user_doc)
        return user

    def reconcile_user_view_progress(self, user, user_doc):
        if 'nodes' not in user_doc or 'view_progress' not in user_doc['nodes']:
            return
        for node_id, values in user_doc['nodes']['view_progress'].items():
            node = mongo.nodes_collection.find_one({'_id': ObjectId(node_id)})
            file_doc = mongo.files_collection.find_one(
                {'_id': ObjectId(node['properties']['file'])}
            )
            if 'picture' in node:
                thumbnail_file_doc = mongo.files_collection.find_one(
                    {'_id': ObjectId(node['picture'])}
                )
            else:
                thumbnail_file_doc = None
            static_asset = self.get_or_create_static_asset(file_doc, thumbnail_file_doc)

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
        user.profile.full_name = user_doc['full_name']
        if 'settings' in user_doc and 'email_communications' in user_doc['settings']:
            if user_doc['settings']['email_communications'] == 1:
                user.profile.is_subscribed_to_newsletter = True
        user.profile.save()

        if 'auth' in user_doc and user_doc['auth']:
            OAuthUserInfo.objects.get_or_create(
                user=user, oauth_user_id=user_doc['auth'][0]['user_id']
            )

    def reconcile_comment_ratings(self, comment_doc):
        if 'ratings' not in comment_doc['properties']:
            return

        comment = self.get_or_create_comment(comment_doc)
        for rating in comment_doc['properties']['ratings']:
            user = self.get_or_create_user(rating['user'])
            self.console_log(f"Updating ratings for comment {comment.id}")
            models_comments.Like.objects.get_or_create(comment=comment, user=user)

    def get_or_create_comment(self, comment_doc, parent_comment_doc=None):
        try:
            comment = models_comments.Comment.objects.get(slug=str(comment_doc['_id']))
        except models_comments.Comment.DoesNotExist:
            # Get the comment author
            user = self.get_or_create_user(comment_doc['user'])
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
            self.console_log(f"Setting parent to comment")
            parent_comment = self.get_or_create_comment(parent_comment_doc)
            comment.reply_to = parent_comment
            comment.save()
        return comment

    def reconcile_file_field(
        self, file_uuid, instance, attr_name, variation_subdoc=None, force=False
    ):
        """Download file from cloud storage and upload to S3."""
        file_doc = mongo.files_collection.find_one({'_id': ObjectId(file_uuid)})

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
            file_path = (
                file_doc['file_path'] if not variation_subdoc else variation_subdoc['file_path']
            )
            dest_file_path_s3 = files.generate_s3_path(file_path)

            # Check if file is already on S3
            if files.file_on_s3(
                files.s3_client, settings.AWS_STORAGE_BUCKET_NAME, dest_file_path_s3
            ):
                print(f"File {dest_file_path_s3} already exists on S3, skipping upload")
                setattr(instance, attr_name, dest_file_path_s3)
                instance.save()
                return

            # Download file
            downloaded_file_path: Optional[pathlib.Path] = files.download_file_from_storage(
                file_doc, tmp_path, variation_subdoc
            )
            # Set value on instance
            if not downloaded_file_path:
                self.console_log(f"\tSkipping non existing file {file_uuid}")
                return
            # Upload to S3
            files.upload_file_to_s3(str(downloaded_file_path), dest_file_path_s3)
            setattr(instance, attr_name, dest_file_path_s3)
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

        if 'duration' in file_doc['variations'][0]:
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
        self.console_log(f"Reconciling file {file_doc['_id']} {file_doc['file_path']}")
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
        static_asset.user = self.get_or_create_user(file_doc['user'])
        static_asset.save()

        self.reconcile_file_field(file_doc['_id'], static_asset, 'source')
        if thumbnail_file_doc:
            self.reconcile_file_field(thumbnail_file_doc['_id'], static_asset, 'thumbnail')

        if static_asset.source_type == 'video':
            self.reconcile_static_asset_video(file_doc, static_asset)

        if static_asset.source_type == 'image':
            self.reconcile_static_asset_image(file_doc, static_asset)

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
                original_filename=file_doc['name'],
                size_bytes=file_doc['length'],
                user_id=1,
                slug=file_slug,
            )

        self.reconcile_static_asset(file_doc, static_asset, thumbnail_file_doc)

        if 'video' in file_doc['content_type'] and 'variations' in file_doc:
            for v in file_doc['variations']:
                self.console_log(f"\tProcessing variation {v['file_path']}")
                if v['file_path'].endswith('.webm'):
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

        return static_asset
