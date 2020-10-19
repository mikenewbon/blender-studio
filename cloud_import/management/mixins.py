import pytz
import tempfile
import pathlib
import datetime
from bson import ObjectId
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from blender_id_oauth_client.models import OAuthUserInfo
from cloud_import.management import mongo
import static_assets.models as models_static_assets
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

    def reconcile_user(self, user, user_doc):
        def reconcile_view_progress():
            if 'nodes' in user_doc and 'view_progress' in user_doc['nodes']:
                for node_id, values in user_doc['nodes']['view_progress'].items():
                    print(node_id)
                    node = mongo.nodes_collection.find_one({'_id': ObjectId(node_id)})
                    video_id = node['properties']['file']
                    static_asset = models_static_assets.StaticAsset.objects.get(slug=str(video_id))
                    print(static_asset)

        self.console_log(f"\t Reconciling user {user_doc['username']}")
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

        # reconcile_view_progress()

    def reconcile_file_field(
        self, file_uuid, instance, attr_name, variation_subdoc=None, force=False
    ):
        """Download file from cloud storage and upload to S3."""
        file_doc = mongo.files_collection.find_one({'_id': ObjectId(file_uuid)})

        if getattr(instance, attr_name) and not force:
            self.console_log(f"\tSkipping existing file {file_uuid}")
            return

        with tempfile.TemporaryDirectory() as tmp_dirname:
            self.console_log(f"Created temporary directory {tmp_dirname}")
            tmp_path = pathlib.Path(tmp_dirname)
            # Download file
            downloaded_file_path = files.download_file_from_storage(
                file_doc, tmp_path, variation_subdoc
            )
            # Set value on instance
            file_path = (
                file_doc['file_path'] if not variation_subdoc else variation_subdoc['file_path']
            )
            file_path_s3 = files.generate_s3_path(file_path)
            setattr(instance, attr_name, file_path_s3)
            instance.save()
            # Upload to S3
            if not downloaded_file_path:
                return
            files.upload_file_to_s3(str(downloaded_file_path), file_path_s3)

    def reconcile_static_asset(self, file_doc, static_asset: models_static_assets.StaticAsset):
        self.console_log(f"Reconciling {file_doc['_id']}")
        # Update properties
        static_asset.slug = str(file_doc['_id'])
        # Update original_filename
        static_asset.original_filename = file_doc['name']
        # Update filesize
        static_asset.size_bytes = file_doc['length']
        # Update date_created
        static_asset.date_created = pytz.utc.localize(file_doc['_created'])
        static_asset.date_updated = pytz.utc.localize(file_doc['_updated'])
        # Update content_type
        static_asset.content_type = file_doc['content_type']
        static_asset.user = self.get_or_create_user(file_doc['user'])
        static_asset.save()

        try:
            video = static_asset.video
            if 'duration' in file_doc:
                video.duration = datetime.timedelta(seconds=file_doc['duration'])
            if 'size' in file_doc:
                video.resolution_label = file_doc['size']
            if 'height' in file_doc:
                video.height = file_doc['height']
            if 'width' in file_doc:
                video.width = file_doc['width']
            video.save()
        except models_static_assets.Video.DoesNotExist:
            pass

        try:
            image = static_asset.image
            image.height = file_doc['height']
            image.width = file_doc['width']
            image.save()
        except models_static_assets.Image.DoesNotExist:
            pass

    def get_or_create_static_asset(self, file_doc):
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

        self.reconcile_static_asset(file_doc, static_asset)

        if 'video' in file_doc['content_type'] and 'variations' in file_doc:
            for v in file_doc['variations']:
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
