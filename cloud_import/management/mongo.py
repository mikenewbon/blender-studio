import os

import requests
from bson import json_util
from google.cloud import storage
from pymongo import MongoClient
import pathlib

overwrite = False

DATABASE_NAME = "cloud_prod"

dirname = os.path.dirname(__file__)
dirname_abspath = pathlib.Path(os.path.abspath(dirname)).parent
client = MongoClient()
db = client[DATABASE_NAME]
projects_collection = db.projects
files_collection = db.files
nodes_collection = db.nodes
users_collection = db.users
# google_storage_client = storage.Client.from_service_account_json(
#     dirname_abspath / "blender-cloud-credentials.json"
# )


def dump_doc(doc, path):
    # Transform mongo objects to string
    training_index = json_util.dumps(doc)
    print(f"Writing {path}")
    # Dump the string on the filesystem
    with open(str(path), "w") as write_file:
        write_file.write(training_index)


def load_doc(path: pathlib.Path):
    with open(str(path), "r") as read_file:
        return json_util.loads(read_file.read())


def get_dir_paths(path) -> list:
    """Generic utility to list subdirectories of a directory."""
    dir_paths = []
    for entry in os.scandir(path):
        if entry.is_dir():
            dir_paths.append(entry)
    return dir_paths


def download_file_from_storage(file_dir_path: pathlib.Path):
    """Fetch a file from storage and save it locally."""

    def download_blob_to_file(project, filepath, destination_filepath):
        """Download a blob from GCS.

        file_doc can be a file document or a variation subdocument
        """
        bucket = google_storage_client.get_bucket(str(project))
        blob = bucket.get_blob(f"_/{filepath}")
        if not blob:
            print(f"Blob {destination_filepath.name} does not exist")
            return
        if blob and blob.exists():
            if not destination_filepath.exists() or overwrite:
                print(f"Downloading {destination_filepath.name}")
                blob.download_to_filename(str(destination_filepath))
            else:
                print(f"Blob {destination_filepath.name} already downloaded")

    def download_static_to_file(url, destination_filepath):
        if destination_filepath.exists() and overwrite is False:
            print(f"File {destination_filepath.name} already downloaded")
            return
        print(f"Requesting {url}")
        r = requests.get(url, allow_redirects=True)
        open(destination_filepath, "wb").write(r.content)

    def download_to_file(file_doc, file_path, file_dir_path, is_variation=False):
        if is_variation:
            variations_abspath = file_dir_path / "variations"
            variations_abspath.mkdir(parents=True, exist_ok=True)
            destination_filepath = variations_abspath / pathlib.Path(v["file_path"]).name
        else:
            destination_filepath = file_dir_path / pathlib.Path(file_doc["file_path"]).name

        if file_doc["backend"] == "gcs":
            download_blob_to_file(file_doc["project"], file_path, destination_filepath)
        elif file_doc["backend"] == "pillar":
            download_static_to_file(file_doc["link"], destination_filepath)
        else:
            print(f"[WARNING]: Backend {file_doc['backend']} is not supported")
            return

    file_doc = load_doc(file_dir_path / "file.json")
    print(f"\tFetching {file_doc['_id']} {file_doc['name']}")
    download_to_file(file_doc, file_doc["file_path"], file_dir_path)
    # destination_filepath = file_dir_path / pathlib.Path(file_doc['file_path']).name
    #
    # if file_doc['backend'] == 'gcs':
    #     download_blob_to_file(file_doc['project'], file_doc['file_path'], destination_filepath)
    # elif file_doc['backend'] == 'pillar':
    #     download_static_to_file(file_doc['link'], destination_filepath)
    # else:
    #     print(f"[WARNING]: Backend {file_doc['backend']} is not supported")
    #     return

    if "video" in file_doc["content_type"] and "variations" in file_doc:
        # variations_abspath = file_dir_path / 'variations'
        # variations_abspath.mkdir(parents=True, exist_ok=True)
        for v in file_doc["variations"]:
            download_to_file(file_doc, v["file_path"], file_dir_path, is_variation=True)
            # var_destination_filepath = variations_abspath / pathlib.Path(v['file_path']).name
            # if file_doc['backend'] == 'gcs':
            #     download_blob_to_file(file_doc['project'], v['file_path'], var_destination_filepath)
            # elif file_doc['backend'] == 'pillar':
            #     download_static_to_file(file_doc['link'], var_destination_filepath)
            # else:
            #     print(f"[WARNING]: Backend {file_doc['backend']} is not supported")
            #     return


def download_files(training_abspath: pathlib.Path):
    """Download all files inside a /files training directory."""
    files_abspath = training_abspath.joinpath("files")
    for file_dir_path in get_dir_paths(files_abspath):
        download_file_from_storage(pathlib.Path(file_dir_path))
