import os
import pathlib
import shutil
from bson import json_util

from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings

from static_assets import models as models_assets
from common import upload_paths


class Command(BaseCommand):
    help = 'Import legacy Blender Cloud Training'

    def add_arguments(self, parser):
        parser.add_argument('training_dir', type=str)
        parser.add_argument(
            '-s', '--slug', dest='training_names', action='append', help="provides training slugs"
        )
        parser.add_argument(
            '--all', action='store_true', help='Import all trainings in the directory',
        )

    def load_doc(self, path: pathlib.Path):
        with open(str(path), "r") as read_file:
            return json_util.loads(read_file.read())

    def add_local_file(self, model, field_name, filepath: pathlib.Path):
        with open(str(filepath), 'rb') as f:
            django_file = File(f)
            setattr(model, field_name, django_file)
            model.save()

    def import_training(self, training_abspath):
        from training import models as models_training

        training_doc_path = training_abspath / 'index.json'
        training_doc = self.load_doc(training_doc_path)

        def add_static_asset_path(ob, property, file_path):
            # Build the full path for the file. In Blender Cloud there is a convention to place all
            # assets in a "_" directory at the root of the bucket.
            file_path_full = f"_/{file_path}"
            setattr(ob, property, file_path_full)
            ob.save()

        def add_images_to_training(training):
            # Add images for the project
            training_pictures = {'thumbnail', 'picture_header'}
            for picture in training_pictures:
                self.stdout.write(self.style.NOTICE('Adding pictures for training %s' % training))
                file_doc_path = (
                    training_doc_path.parent / 'files' / str(training_doc[picture]) / 'file.json'
                )
                file_doc = self.load_doc(file_doc_path)
                add_static_asset_path(training, picture, file_doc['file_path'])

                # file_path_src = file_doc_path.parent / pathlib.Path(file_doc['file_path']).name
                # file_path_rel = upload_paths.get_upload_to_hashed_path(
                #     training, pathlib.Path(file_doc['file_path']).name
                # )
                # file_path_dst = pathlib.Path(settings.MEDIA_ROOT, file_path_rel)
                # # Ensure destination directory
                # file_path_dst.parent.mkdir(parents=True, exist_ok=True)
                # # shutil.copy(str(file_path_src), str(file_path_dst))
                # setattr(training, picture, str(file_path_rel))
                # training.save()

        def get_or_create_training():
            # Fetch or create Training object
            self.stdout.write(self.style.NOTICE('Creating training %s' % training_doc['url']))
            if models_training.trainings.Training.objects.filter(slug=training_doc['url']).exists():
                training = models_training.trainings.Training.objects.get(slug=training_doc['url'])
                self.stdout.write(
                    self.style.WARNING('Project %s already exists' % training_doc['url'])
                )
            else:
                training = models_training.trainings.Training.objects.create(
                    name=training_doc['name'],
                    slug=training_doc['url'],
                    description=training_doc['summary'],
                    summary=training_doc['description'],
                    status=training_doc['status'],
                    type=training_doc['category'],
                    difficulty='beginner',
                )

            return training

        def get_or_create_chapters(training):
            # Create Chapters
            training_chapters_path = training_abspath / 'chapters'

            chapter_index = 1
            for chapter_dir in os.listdir(training_chapters_path):
                chapter_doc = self.load_doc(training_chapters_path / chapter_dir / 'index.json')
                chapter_slug = str(chapter_doc['_id'])

                self.stdout.write(self.style.NOTICE('Creating chapter %s' % chapter_slug))
                chapter = models_training.chapters.Chapter.objects.get_or_create(
                    index=chapter_index,
                    training=training,
                    name=chapter_doc['name'],
                    slug=chapter_slug,
                )[0]

                date_created = chapter_doc['_created']
                date_updated = (
                    chapter_doc['_created']
                    if '_updated' not in chapter_doc
                    else chapter_doc['_updated']
                )
                models_training.chapters.Chapter.objects.filter(pk=chapter.pk).update(
                    date_created=date_created, date_updated=date_updated
                )
                chapter_index += 1
                self.stdout.write(self.style.NOTICE('Creating sections for %s' % chapter_slug))
                get_or_create_sections(chapter)

        def attach_video_or_asset_to_section(section, section_doc, date_created, date_updated):
            file_doc_path = (
                training_doc_path.parent
                / 'files'
                / str(section_doc['properties']['file'])
                / 'file.json'
            )
            file_doc = self.load_doc(file_doc_path)

            # Create video
            if section_doc['properties']['content_type'] == 'video':
                # Proceed only if a version is found, and pick the first only
                if 'variations' not in file_doc:
                    return

                try:
                    video = section.video
                except models_training.sections.Video.DoesNotExist:
                    video = models_training.sections.Video.objects.create(
                        section=section, size=25000, duration='10:00', file='stand/in/path.mp4',
                    )
                models_training.sections.Video.objects.filter(pk=video.pk).update(
                    date_created=date_created, date_updated=date_updated
                )

                variation = file_doc['variations'][0]
                add_static_asset_path(video, 'file', variation['file_path'])

            elif section_doc['properties']['content_type'] == 'file':
                if section.assets.exists():
                    asset = section.assets.first()
                else:
                    asset = models_training.sections.Asset.objects.create(
                        section=section, size=25000, file='stand/in/path.mp4',
                    )
                add_static_asset_path(asset, 'file', file_doc['file_path'])
                models_training.sections.Asset.objects.filter(pk=asset.pk).update(
                    date_created=date_created, date_updated=date_updated
                )

            # file_path_src = (
            #     file_doc_path.parent / 'variations' / pathlib.Path(variation['file_path']).name
            # )
            # file_path_rel = upload_paths.get_upload_to_hashed_path(
            #     video, pathlib.Path(variation['file_path']).name
            # )
            # file_path_dst = pathlib.Path(settings.MEDIA_ROOT, file_path_rel)
            # # Ensure destination directory
            # file_path_dst.parent.mkdir(parents=True, exist_ok=True)
            # # Copy only if files don't exist
            # if not file_path_dst.exists():
            #     pass
            #     # shutil.copy(str(file_path_src), str(file_path_dst))
            # setattr(video, 'file', str(file_path_rel))
            # video.save()

        def get_or_create_sections(chapter):
            chapter_abspath = training_abspath / 'chapters' / chapter.slug

            section_index = 1
            for section_dir in os.scandir(chapter_abspath):
                if section_dir.is_file():
                    continue
                section_doc = self.load_doc(chapter_abspath / section_dir / 'index.json')
                self.stdout.write(self.style.NOTICE('Creating section %s' % section_doc['name']))

                # if 'order' in section_doc['properties']:
                #     section_index = section_doc['properties']['order']

                section = models_training.sections.Section.objects.get_or_create(
                    index=section_index,
                    chapter=chapter,
                    name=section_doc['name'],
                    slug=str(section_doc['_id']),
                    text=section_doc['description'],
                )[0]
                date_created = section_doc['_created']
                date_updated = (
                    section_doc['_created']
                    if '_updated' not in section_doc
                    else section_doc['_updated']
                )
                models_training.sections.Section.objects.filter(pk=section.pk).update(
                    date_created=date_created, date_updated=date_updated
                )
                section_index += 1
                attach_video_or_asset_to_section(section, section_doc, date_created, date_updated)

        training = get_or_create_training()
        add_images_to_training(training)
        get_or_create_chapters(training)
        # Create Sections

        self.stdout.write(self.style.SUCCESS('All is great'))

    def handle(self, *args, **options):
        dirname_abspath = pathlib.Path(options['training_dir'])

        if options['all']:
            for entry in os.scandir(dirname_abspath):
                if entry.is_dir():
                    self.import_training(dirname_abspath / entry)
            return

        for training_name in options['training_names']:
            self.import_training(dirname_abspath / training_name)
