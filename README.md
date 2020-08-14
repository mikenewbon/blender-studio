# Blender Studio

Blender Studio is the creative hub for your projects, powered by Free and Open Source Software.
Follow along with our expert team at your own pace - on every subject from Animation to UV unwrapping.
Classes, workshops and production lessons with .blend files included.
With 400+ hours of training and 1000's of production files, you're getting the best resources
Blender has to offer.


## Development

The project is written in Django, with Django templates and some Java Script.

The full developer documentation is in the [docs folder](docs).

### Table of contents
 - [Development](docs/development.md)
    1. [Requirements](docs/development.md#requirements)
    2. [Set up instructions](docs/development.md#set-up-instructions)
    3. [Data import](docs/development.md#data-import)
    4. [Blender ID authentication](docs/development.md#blender-id-authentication-setup)
    5. [Search](docs/development.md#search-setup)
    6. [Workflow](docs/development.md#workflow)
 - [Search](docs/search.md)
    1. [Overwiew](docs/search.md#overview)
        - [Indexing blog posts](docs/search.md#indexing-blog-posts)
    2. [Management commands](docs/search.md#management-commands)
    3. [Deployment to production](docs/search.md#deployment-to-production)
        - [Nginx config](docs/search.md#nginx-config)
        - [Authentication](docs/search.md#authentication)
    4. [Troubleshooting](docs/search.md#troubleshooting)
        - [Updating index settings](docs/search.md#updating-index-settings)
        - [Recreating an index](docs/search.md#recreating-an-index)
        - [Updating indexed documents](docs/search.md#updating-indexed-documents)
 - [Architecture Overview](docs/architecture.md)
    1. [Models (simplified) hierarchy](docs/architecture.md#models-simplified-hierarchy)
 - [Miscellaneous facts](docs/miscellaneous.md)
    1. [Templates](docs/miscellaneous.md#templates)
        - [Jinja](docs/miscellaneous.md#jinja)
        - [Typed templates](docs/miscellaneous.md#typed-templates)
    2. [Media files](docs/miscellaneous.md#media-files)
    3. [URLs](docs/miscellaneous.md#urls)
    4. [Asset modals](docs/miscellaneous.md#asset-modals)
