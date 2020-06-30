# Architecture Overview

Apps:
 - [assets](#assets)
 - [blog](#blog)
 - [comments](#comments)
 - [films](#films)
 - [subscriptions](#subscriptions)
 - [training](#training)

Additionally:
 - `common` directory - contains the code that is used (or we plan to use it) in more than one app:
 scripts, template bases or components, test factories, etc.
 
To be extracted to a separate app:
 - [progress](#progress)
 
TODO:
 - [user and profile](#user-profile)
 - flat pages - e.g. an "About" page of a film
 
Other:
 - **Project** - this word may refer to a film or a training. In production, there'll be exactly one
 storage backend (GCS, S3, etc.) per project. We don't have a `Project` model at the moment, but
 there's a chance that it changes in the future.
 
## Assets

**Static Assets** represent the files uploaded in the cloud.

Static assets can be of three types (`source_type` attribute): image, video, or (a generic) file.

**Images** and **Videos** should be represented by their respective models: `Image` and `Video`,
which provide additional attributes like resolution or duration. These models additionally 
have a one-to-one reference to a Static Asset instance, containing all the other data.

Preview pictures for image and video can be generated automatically (e.g. by the `sorl-thumbnail`
library), but for the `file` source type, adding a preview is obligatory.

We want the entire `assets` app (i.e. file-representing models: `StaticAsset`, `Image`, `Video`)
to be portable, and independent of the other apps. In particular, the `DynamicStorageFileField`
should be left inside this app, even though it is used in other apps' models as well.

**Licenses:**
For now, we only have licenses for film-related resources. They are obligatory for any
static asset (image, video, file).

**Storage Backends:** ...
 
 
## Blog
WIP at an early stage.

Sem started working on the models in the 'blog' app. Posts will usually be related to films,
and displayed in the 'weeklies' section alongside production logs. However, it could be potentially
useful to be able to also add posts about trainings.
 
## Comments

Comments are a self-contained, reusable app. We don't want to have to change their models 
whenever they are reused for another app, so they shouldn't be linked to external models in any way.

How to add comments to a new model — say, `Asset`:

- define an intermediary model for `Comment` and `Asset`, e.g. `AssetComment`,
- in `AssetComment`, add a `ForeignKey` to `Asset`,
- add a `OneToOneField` to `Comment` (each `AssetComment` should only relate to one `Comment`).


## Films



**Collections** can contain film-related assets. They can also contain other collections (nested
collections, child collections). For now, the front end does not expect nested collections to
contain further nested collections. However, this restriction does not apply at the database level.

**Asset (model in films app) vs. StaticAsset (model in assets app):**  

- Static Asset is more "low-level" and represents an uploaded file; we want to have a less 
generic model that could be extracted and reused in other apps (e.g. blog, training). 
Therefore Static Asset should not contain any relationships to other apps.
- Asset contains the metadata, and represents the web page where the file (artwork, training video, etc.)
is displayed. As a model in the 'films' app, asset may belong to a Collection, and is a part (leaf)
of the tree-like structure of film-related resources.


Caution: There's also an `Asset` model in the training app, but it represents a slightly different 
thing: it is an additional file related to a training section (not its main video).


**Production Logs / Weeklies:**
The production logs are also called "weeklies" or "production weeklies" in the website and the admin
panel. We stick to "production logs" in the back end code, though. 

- **ProductionLog** — all the log entries from one week. This is akin to a blog post, and can be shown
in the project timeline along with the blog posts (or a blog post could just mention that there's
a new production log available, and link to it). 

- **ProductionLogEntry** — contains multiple assets, all created by one author during a particular week

- **ProductionLogEntryAsset** — an intermediary table between the `Asset` and `ProductionLogEntry` models.  

At the moment, we don't consider it necessary to have any relation between a production log and a
blog post on the database level. This can all be handled manually.

Probably we'll need slugs for these objects later.


## Progress
Could be extracted to a separate app. Has to be added to films, too.


## Subscriptions
...


## Training

A training consists of chapters, which in turn are made up of sections.

Sections within a chapter are ordered by their `index` attribute. So are chapters in a training.

Each **Section** contains a video (its main content), represented by the **Video** model.
It can also contain an arbitrary number of other files, stored as **Asset** instances.
A section can have comments (from the [comments](#comments) app, linked via the **SectionComment**
model).

The training Asset model should not be confused with an identically named model in the films app.



## User and Profile
For now, we use the Django's default `User` model.

In the future, we'll most likely have a `Profile` with a `OneToOneField` to `User`.
It enables creating profiles without registering users, as well as swapping profiles easily when
a new user, for whom a profile has been created by admin, registers an account (this proved useful
in the conference website).
