# Search

The search functionality uses [MeiliSearch](https://github.com/meilisearch/MeiliSearch).

## Overview
There is the full-website search available everywhere by clicking on the magnifying
glass icon in the top right-hand corner of a page, and a training-specific search on the
training home page.

### Full-website search
For the main search, all the indexed documents are stored under one index, `studio`. This
name (the uid of the index) is defined in settings.py, in the `MEILISEARCH_INDEX_UID`
variable.
Two replica indexes are created and kept in sync with the main index: `studio_date_asc`
and `studio_date_desc`. They are used for search results' alternative ordering.

The models that are 'searchable', i.e. added to the index, are:
 - films.Film - the published ones,
 - films.Asset - the published ones that belong to a published film,
 - training.Training - the published ones,
 - training.Section - belonging to a published training,
 - blog.Post - the published ones.

### Training search
For the training search, there is a separate index `training` (`TRAINING_INDEX_UID`
in settings.py). The searchable models are:
 - training.Training - the published ones,
 - training.Section - belonging to a published training,
 - films.Asset - only Production Lessons which are also published.

## Indexing
Each document in any index needs to have a unique ID field. The field is called `search_id`
and is generated based on the model and the object `pk`, e.g. `film_1` for the film with
`pk=1`.

Django signals take care of indexing new objects in the database or updating the existing
ones on change: a `post_save` signal is attached to each of the above mentioned models.
When an object is updated in the database, it is 'added' to the appropriate indexes with
the same `search_id`, which means that no new document is created, only the existing one
is updated.

On object deletion, the related document will be deleted from the index thanks to a
`pre_delete` signal.

It is also possible to update the indexes with all the documents in the database using a
Django management command:
```
./manage.py index_documents
```
For more details, see the command's `--help` or the
[search setup instructions](#adding-documents-to-the-search-index).

## Management commands
Two Django management commands are available:
 - `create_search_indexes` - creates a new 'main' index, with the uid `MEILISEARCH_INDEX_UID`,
 two replica indexes used for alternative search results ordering, and an index for the
 search in training.
 If the indexes already exists, the command only updates their settings to the values they
 are expected to have.
 - `index_documents` - adds documents from the database to all the indexes.
 If a document with a given `search_id` is already present in an index, it will be updated.

The commands can be run from the Bash console with the project's venv activated:
```
./manage.py create_search_indexes
./manage.py index_documents
```

## Troubleshooting
If the search does not work as expected, it may be due to some index settings being out of
date or the documents in the index being out of date.

### Updating index settings
To update the indexes' **settings** - such as fields used for faceting, searchable fields,
ranking rules etc. - run the `create_search_indexes` command. If the indexes exist, it does
not create new ones, only resets their settings to the desired values.
```
./manage.py create_search_indexes
```

### Recreating an index
Some settings (the index name, the index primary key field name) cannot be updated.
If you need to change them, you have to delete the old index and create it again.
Note that this will also delete all the indexed documents.
An index can be [deleted in a few ways](https://docs.meilisearch.com/references/indexes.html#delete-an-index),
e.g.:
 1. In Bash console:
     ```
    curl -X DELETE 'http://localhost:7700/indexes/studio'
     ```
 2. In Django shell (`./manage.py shell`):
     ```
    import meilisearch
    meilisearch.Client('http://localhost:7700').get_index('studio').delete()
     ```
Also note that usually you'll have to delete the replica indexes as well.

After deleting all the indexes, recreate and set them up by running:
```
./manage.py create_search_indexes
```

### Updating indexed documents
If the data in the database or the documents' structure changes, run the `index_documents`
command. It updates the existing documents (based on a matching `search_id`), so no duplicate
documents should be added to the index.
```
./manage.py index_documents
```
