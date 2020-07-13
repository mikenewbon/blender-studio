from django import template

register = template.Library()


@register.inclusion_tag('films/components/breadcrumbs.html', takes_context=True)
def show_breadcrumbs(context):
    """
    Creates a breadcrumb navigation for :template:`films/gallery.html` and
    :template:`films/collection_detail.html`.

    Breadcrumbs have links to the film and the collection hierarchy above the current
    collection. The current location name is also included, but without a link.

    **Tag template:**

    :template:`films/components/breadcrumbs.html`
    """
    breadcrumbs = []
    film = context['film']
    collection = context.get('current_collection')
    if collection:
        current_location = collection.name

        while collection.parent:
            breadcrumbs.append((collection.parent.name, collection.parent.url))
            collection = collection.parent

        breadcrumbs.append((film.title, film.url))
    else:
        current_location = film.title

    return {
        'breadcrumbs': breadcrumbs[::-1],
        'current_location': current_location,
    }
