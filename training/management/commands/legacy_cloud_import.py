import os
import pathlib
import shutil
from bson import json_util

from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings


class Command(BaseCommand):
    help = 'Import legacy Blender Cloud Training'

    def add_arguments(self, parser):
        parser.add_argument('training_dir', type=str)

    def load_doc(self, path: pathlib.Path):
        with open(str(path), "r") as read_file:
            return json_util.loads(read_file.read())

    def add_local_file(self, model, field_name, filepath: pathlib.Path):
        with open(str(filepath), 'rb') as f:
            django_file = File(f)
            setattr(model, field_name, django_file)
            model.save()

    def handle(self, *args, **options):
        from training import models as models_training

        dirname_abspath = pathlib.Path(options['training_dir'])

        training_doc_path = dirname_abspath / 'track-match-blend' / 'index.json'
        training_doc = self.load_doc(training_doc_path)

        def get_or_create_training():
            # Fetch or create Training object
            if models_training.trainings.Training.objects.filter(slug=training_doc['url']).exists():
                training = models_training.trainings.Training.objects.get(slug=training_doc['url'])
                self.stdout.write(self.style.WARNING('Project %s already exists' % training_doc['url']))
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
            # Add images for the project
            training_pictures = {'picture_16_9', 'picture_header'}
            for picture in training_pictures:
                file_doc_path = training_doc_path.parent / 'files' / str(training_doc[picture]) / 'file.json'
                file_doc = self.load_doc(file_doc_path)
                file_path_src = file_doc_path.parent / pathlib.Path(file_doc['file_path']).name
                file_path_rel = models_training.training_overview_upload_path(training, pathlib.Path(file_doc['file_path']).name)
                file_path_dst = pathlib.Path(settings.MEDIA_ROOT, file_path_rel)
                # Ensure destination directory
                file_path_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(file_path_src), str(file_path_dst))
                # self.add_local_file(training, 'picture_16_9', file_path_rel)
                setattr(training, picture, file_path_rel)
                training.save()

            return training

        def get_or_create_chapters(training):
            # Create Chapters
            training_chapters_path = dirname_abspath / 'track-match-blend' / 'chapters'

            chapter_index = 1
            for chapter_dir in os.listdir(training_chapters_path):
                chapter_doc = self.load_doc(training_chapters_path / chapter_dir / 'index.json')
                chapter_slug = str(chapter_doc['_id'])

                chapter = models_training.chapters.Chapter.objects.get_or_create(
                    index=chapter_index,
                    training=training,
                    name=chapter_doc['name'],
                    slug=chapter_slug,
                )[0]
                chapter_index += 1
                get_or_create_sections(chapter)

        def get_or_create_sections(chapter):
            chapter_abspath = dirname_abspath / chapter.training.slug / 'chapters' / chapter.slug

            section_index = 1
            for section_dir in os.scandir(chapter_abspath):
                if section_dir.is_file():
                    continue
                section_doc = self.load_doc(chapter_abspath / section_dir / 'index.json')
                section = models_training.sections.Section.objects.get_or_create(
                    index=section_index,
                    chapter=chapter,
                    name=section_doc['name'],
                    slug=str(section_doc['_id']),
                    text=section_doc['description'],
                )[0]
                section_index += 1

                # Create video, if available
                if section_doc['properties']['content_type'] != 'video':
                    continue

                file_doc_path = training_doc_path.parent / 'files' / str(
                    section_doc['properties']['file']) / 'file.json'
                file_doc = self.load_doc(file_doc_path)

                # Proceed only if a version is found, and pick the first only
                if 'variations' not in file_doc:
                    continue

                try:
                    video = section.video
                except models_training.sections.Video.DoesNotExist:
                    video = models_training.sections.Video.objects.create(
                        section=section,
                        size=25000,
                        duration='10:00',
                        file='stand/in/path.mp4'
                    )

                variation = file_doc['variations'][0]

                file_path_src = file_doc_path.parent / 'variations' / pathlib.Path(variation['file_path']).name
                file_path_rel = models_training.sections.video_upload_path(
                    video, pathlib.Path(variation['file_path']).name)
                file_path_dst = pathlib.Path(settings.MEDIA_ROOT, file_path_rel)
                # Ensure destination directory
                file_path_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(file_path_src), str(file_path_dst))
                # self.add_local_file(training, 'picture_16_9', file_path_rel)
                setattr(video, 'file', file_path_rel)
                video.save()

        training = get_or_create_training()
        get_or_create_chapters(training)
        # Create Sections

        self.stdout.write(self.style.SUCCESS('All is great'))
