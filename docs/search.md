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


## Deployment to production
MeiliSearch is deployed more or less according to [the tutorial](https://docs.meilisearch.com/running-production),
but it does not have SSL set up.
It is run as a service, and the requests to it are routed via nginx.

### Nginx config
Nginx config can be found in the `var/www/config` directory. Add a `location` for search:
```
    # Meilisearch
    location /s/ {
        rewrite /s/(.*) /$1  break;
        proxy_pass  http://127.0.0.1:7700;
    }
```
Since all the search requests have to be sent to `https://studiobeta.blender.org/s/`,
update the `MEILISEARCH_API_ADDRESS` variable in `settings.py`:
```
MEILISEARCH_API_ADDRESS = 'https://studiobeta.blender.org/s/'
```

### Authentication
Use the master key (the same that you passed to MeiliSearch's `ExecStart` command) to retrieve
the public and the private key:
```
curl -H "X-Meili-API-Key: myMasterKey" -X GET 'http://localhost:7700/keys'
```
Update `settings.py` with these values:
```
MEILISEARCH_PUBLIC_KEY = 'PublicKeyGoesHere'
MEILISEARCH_PRIVATE_KEY = 'PrivateKeyHere'
```

#### How it works
In production, the server should be run in the `Production` mode, and with a master key.
Running the server without a master key is only possible in the development mode, as it makes
all routes accessible and constitutes a security issue.
The details are explained in [the authentication guide](https://docs.meilisearch.com/guides/advanced_guides/authentication.html).

What is important here is that when the server is running with a master key, all the requests
sent to it have to include the `X-Meili-API-Key` header with either the public key (for search
requests), or the private key (for all other requests). In practise, the front end needs the
public key, and the back end (management commands, signals) - the private one.

When you change the master key, the public and private keys change too, and you will have to
update them in `settings.py`.


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
