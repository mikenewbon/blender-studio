import datetime
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
    help = 'Import legacy Blender Cloud Film'

    def add_arguments(self, parser):
        parser.add_argument('film_dir', type=str)
        parser.add_argument(
            '-s', '--slug', dest='film_names', action='append', help="provides film slugs"
        )
        parser.add_argument('--all', action='store_true', help='Import all films in the directory')

    def load_doc(self, path: pathlib.Path):
        with open(str(path), "r") as read_file:
            return json_util.loads(read_file.read())

    def add_local_file(self, model, field_name, filepath: pathlib.Path):
        with open(str(filepath), 'rb') as f:
            django_file = File(f)
            setattr(model, field_name, django_file)
            model.save()

    def get_file_object(self, film_doc_path, file_id):
        self.stdout.write(self.style.NOTICE(f"\tGetting file {file_id}"))
        file_doc_path = film_doc_path.parent / 'files' / str(file_id) / 'file.json'
        return self.load_doc(file_doc_path)

    def add_static_asset_path(self, ob, property, file_path):
        # Build the full path for the file. In Blender Cloud there is a convention to place all
        # assets in a "_" directory at the root of the bucket.
        file_path_full = f"_/{file_path}"
        setattr(ob, property, file_path_full)
        ob.save()

    def import_film(self, film_abspath):
        from films import models as models_film

        film_doc_path = film_abspath / 'index.json'
        film_doc = self.load_doc(film_doc_path)

        def add_static_asset_path(ob, property, file_path):
            # Build the full path for the file. In Blender Cloud there is a convention to place all
            # assets in a "_" directory at the root of the bucket.
            file_path_full = f"_/{file_path}"
            setattr(ob, property, file_path_full)
            ob.save()

        def add_images_to_film(film):
            # Add images for the project
            film_pictures = {'picture_header'}
            for picture in film_pictures:
                self.stdout.write(self.style.NOTICE('Adding pictures for film %s' % film))
                file_doc_path = (
                    film_doc_path.parent / 'files' / str(film_doc[picture]) / 'file.json'
                )
                file_doc = self.load_doc(file_doc_path)
                add_static_asset_path(film, picture, file_doc['file_path'])
            # Add Poster and logo
            film_pictures = {'poster', 'logo'}
            for picture in film_pictures:
                file_doc_path = (
                    film_doc_path.parent
                    / 'files'
                    / str(film_doc['extension_props']['cloud'][picture])
                    / 'file.json'
                )
                file_doc = self.load_doc(file_doc_path)
                add_static_asset_path(film, picture, file_doc['file_path'])

        def get_or_create_film():
            # Fetch or create Film object
            self.stdout.write(self.style.NOTICE('Creating film %s' % film_doc['url']))
            if models_film.films.Film.objects.filter(slug=film_doc['url']).exists():
                film = models_film.films.Film.objects.get(slug=film_doc['url'])
                self.stdout.write(self.style.WARNING('Project %s already exists' % film_doc['url']))
            else:
                film = models_film.films.Film.objects.create(
                    title=film_doc['name'],
                    slug=film_doc['url'],
                    description=film_doc['summary'],
                    summary=film_doc['description'],
                    status=models_film.FilmStatus.released,
                    picture_header='place/holder.jpg',
                    logo='place/holder.jpg',
                    poster='place/holder.jpg',
                    is_published=True,
                )

            return film

        def get_or_create_collections_and_assets(film):
            # Create Chapters
            film_nodes_path = film_abspath / 'nodes'

            def get_or_create_collection(node_doc, as_parent=False):
                tab_char = "\t" if as_parent else ""
                self.stdout.write(
                    self.style.NOTICE(f"{tab_char}Creating collection {node_doc['_id']}")
                )
                if 'parent' in node_doc and node_doc['parent']:
                    if str(node_doc['_id']) == str(node_doc['parent']):
                        self.stdout.write(self.style.WARNING('Self parent detected'))
                        return
                    parent_node_doc = self.load_doc(
                        film_nodes_path / str(node_doc['parent']) / 'index.json'
                    )
                    parent = get_or_create_collection(parent_node_doc, as_parent=True)
                else:
                    parent = None

                node_id = str(node_doc['_id'])
                description = '' if 'description' not in node_doc else node_doc['description']
                collection = models_film.Collection.objects.get_or_create(
                    film=film,
                    parent=parent,
                    order=1,
                    name=node_doc['name'],
                    text=description,
                    slug=node_id,
                )[0]
                if 'picture' in node_doc and node_doc['picture']:
                    file_doc = self.get_file_object(film_doc_path, str(node_doc['picture']))
                    self.add_static_asset_path(collection, 'preview', file_doc['file_path'])

                models_film.Collection.objects.filter(pk=collection.pk).update(
                    date_created=node_doc['_created'], date_updated=node_doc['_updated']
                )

                return collection

            def get_or_create_asset(node_doc):
                self.stdout.write(self.style.NOTICE(f"Creating asset {node_doc['_id']}"))
                if 'file' not in node_doc['properties']:
                    self.stdout.write(
                        self.style.WARNING(
                            f"File property not found in asset " f"{node_doc['_id']}"
                        )
                    )
                    return
                file_doc = self.get_file_object(film_doc_path, str(node_doc['properties']['file']))
                # Get first variation for video
                # TODO(fsiddi) Handle storage of original file and variations
                if node_doc['properties']['content_type'] == 'video':
                    if 'variations' not in file_doc:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Missing variation in video file " f"{file_doc['_id']}"
                            )
                        )
                        return
                    variation = file_doc['variations'][0]
                    source_path = f"_/{variation['file_path']}"
                else:
                    source_path = f"_/{file_doc['file_path']}"

                static_asset = models_assets.StaticAsset.objects.get_or_create(
                    source=source_path,
                    source_type=node_doc['properties']['content_type'],
                    original_filename=file_doc['name'],
                    size_bytes=file_doc['length'],
                    user_id=1,
                )[0]

                if 'picture' in node_doc and node_doc['picture']:
                    file_doc = self.get_file_object(film_doc_path, str(node_doc['picture']))

                    static_asset.thumbnail = f"_/{file_doc['file_path']}"
                    static_asset.save()

                if node_doc['properties']['content_type'] == 'video':
                    models_assets.Video.objects.get_or_create(
                        static_asset=static_asset, duration_seconds=datetime.timedelta(minutes=5)
                    )
                elif node_doc['properties']['content_type'] == 'image':
                    models_assets.Image.objects.get_or_create(static_asset=static_asset)

                if 'parent' in node_doc and node_doc['parent']:
                    parent_node_doc = self.load_doc(
                        film_nodes_path / str(node_doc['parent']) / 'index.json'
                    )
                    parent = get_or_create_collection(parent_node_doc)
                else:
                    parent = None

                node_id = str(node_doc['_id'])

                description = '' if 'description' not in node_doc else node_doc['description']
                asset = models_film.Asset.objects.get_or_create(
                    film=film,
                    collection=parent,
                    order=order,
                    name=node_doc['name'],
                    description=description,
                    slug=node_id,
                    is_published=True,
                    category='artwork',
                    static_asset=static_asset,
                )[0]

                models_film.Asset.objects.filter(pk=asset.pk).update(
                    date_created=node_doc['_created'], date_updated=node_doc['_updated']
                )

            order = 1
            for node in os.listdir(film_nodes_path):
                node_doc = self.load_doc(film_nodes_path / node / 'index.json')

                if node_doc['node_type'] == 'group':
                    get_or_create_collection(node_doc)
                elif node_doc['node_type'] == 'asset':
                    get_or_create_asset(node_doc)
                order += 1

        film = get_or_create_film()
        add_images_to_film(film)
        get_or_create_collections_and_assets(film)

        self.stdout.write(self.style.SUCCESS(f"All is great for {film.title}"))

    def handle(self, *args, **options):
        dirname_abspath = pathlib.Path(options['film_dir'])

        if options['all']:
            for entry in os.scandir(dirname_abspath):
                if entry.is_dir():
                    self.import_film(dirname_abspath / entry)
            return

        for film_name in options['film_names']:
            self.import_film(dirname_abspath / film_name)
