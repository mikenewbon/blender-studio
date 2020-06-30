# Architecture Overview

Apps:
 - [assets](#assets)
 - [blog](#blog)
 - [comments](#comments)
 - [films](#films)
 - [subscriptions](#subscriptions)
 - [training](#training)

Additionally:
 - `common` directory - contains the code that is used (or we plan to use it) in more than one app
 
To be extracted to a separate app:
 - [progress](#progress)
 
TODO:
 - [user and profile](#user-profile)
 
## Assets

**Licenses:**
For now, we only have licenses for film-related resources. They are obligatory for any
static asset (image, video, file).
 
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



## Progress
Could be extracted to a separate app. Has to be added to films too.


## Subscriptions



## Training


## User, profile
For now, we use the Django's default `User` model. No profile model is necessary at this stage.
In the future, we'll most likely have a `Profile` with a `OneToOneField` to `User`.
It enables creating profiles without registering users, as well as swapping profiles easily when
a new user, for whom a profile has been created by admin, registers an account (this proved useful
in the conference website).
