import os
from bson import json_util

from pymongo import MongoClient
import pathlib

overwrite = False

DATABASE_NAME = "cloud-production-3"

dirname = os.path.dirname(__file__)
dirname_abspath = pathlib.Path(os.path.abspath(dirname)).parent
client = MongoClient()
db = client[DATABASE_NAME]
projects_collection = db.projects
files_collection = db.files
nodes_collection = db.nodes
users_collection = db.users
stats_collection = db.cloudstats


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


# def download_files(training_abspath: pathlib.Path):
#     """Download all files inside a /files training directory."""
#     files_abspath = training_abspath.joinpath("files")
#     for file_dir_path in get_dir_paths(files_abspath):
#         download_file_from_storage(pathlib.Path(file_dir_path))
