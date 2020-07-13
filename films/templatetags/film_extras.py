from django import template

register = template.Library()


@register.inclusion_tag('films/components/breadcrumbs.html', takes_context=True)
def show_breadcrumbs(context):
    """
    Creates the breadcrumbs for :template:`films/gallery.html`.

    Breadcrumbs have links to the film and the collection hierarchy above the current
    collection. The current collection name is also included, but without a link.

    **Tag template:**

    :template:`films/components/breadcrumbs.html`
    """
    breadcrumbs = []
    collection = context.get('current_collection')
    if collection:
        current_collection_name = collection.name

        while collection.parent:
            breadcrumbs.append((collection.parent.name, collection.parent.url))
            collection = collection.parent
    else:
        current_collection_name = 'Featured Artwork'

    film = context['film']
    breadcrumbs.append((film.title, film.url))

    return {
        'breadcrumbs': breadcrumbs[::-1],
        'current_collection_name': current_collection_name,
    }
