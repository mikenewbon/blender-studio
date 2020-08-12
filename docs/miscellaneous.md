# Tricky parts

### Templates
##### Jinja
Templates in some parts of the project used to be rendered with Jinja2. We've rewritten
them all to use the Django template backend. There may also be leftover Jinja macros in
the project; some of them have served as reference, but for the most part they probably
could already be removed.


##### Typed templates
The [training](./architecture.md#training) and [comments](./architecture.md#comments) app use
"typed templates". Other apps have ordinary Django templates and views. The plan is to replace the typed
templates with regular ones in the future.



### Media files
Media files (e.g. static assets, preview images of collections, training section videos, etc. - all the
other files that can be uploaded with model instances, in the entire project) are uploaded to nested
directories inside `MEDIA_ROOT`. Their filenames are hashed to avoid name collisions.

Nesting does not depend on project structure (e.g. chapters in a training, or collections in a film),
but is done only to avoid performance issues with too many files in one directory
([see a related SO question](https://stackoverflow.com/a/466938/4744341)). Files are sorted into
directories based on their hashed filename's two first characters. All the individual uploaded files
are stored in additionally nested directories. This way their related and generated files (different
resolution video variants, auto-generated thumbnails, etc.) can be saved in the same directory as their
'parent' file.


### URLs
It would be nice to have the urls matching the ones in the "old" cloud.

##### Films
For the time being, the urls for film-related resources are separated:
for collections, it's `<film_slug>/<collection_slug>`, and for assets — `<film_slug>/assets/<asset-slug>`.

In the future, however, we would like to set up some routing and use one pattern for both
collections and assets: `<film_slug>/<collection-or-asset_uuid>`, with the slugs being replaced
with uuids to ensure their uniqueness.

##### Training
Training app routing has to be documented yet.


### Asset modals
Film assets are displayed in a couple of places: in Weeklies, in Gallery (in real collections and
in the featured assets 'collection'), in the film detail ('About') page of unreleased films.
They are not loaded on separate pages but in [modal
components](https://getbootstrap.com/docs/4.0/components/modal/).
The modal is exactly the same in all the places, so it can be reused, however the context changes.
Depending on whether we are viewing an asset as a part of a collection or a production log entry,
the previous and next assets have to be different.

The context therefore is defined by a query string `?site_context=...` added to the proper 'api-asset'
URL in all the relevant templates, as well as in the components used to display the modal.
The `site_context` values can be the following:

- `'production_logs'` - for assets inside production log entries (in the 'Weeklies' website section or elsewhere),
- `'featured_artwork'` - for featured assets in the 'Gallery' section,
- `'gallery'` - for assets inside collections in the 'Gallery section.

If the `site_context` query string is missing, the previous and next assets are set to `None`.

Film asset modals could potentially be reused in trainings. That's why they are in the `common` directory.
