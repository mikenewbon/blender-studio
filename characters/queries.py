from django.db.models.query import QuerySet

from characters.models import Character, CharacterVersion, CharacterShowcase


def get_characters() -> 'QuerySet[Character]':
    """Get all characters, ensuring that most of the data used by templates is prefetched."""
    return Character.objects.select_related('film',).prefetch_related(
        'versions',
        'versions__comments',
        'versions__static_asset',
        'likes',
        'versions__comments',
        'versions__comments__user',
    )


def get_published_characters() -> 'QuerySet[Character]':
    """Get only published characters."""
    return get_characters().filter(is_published=True)


def get_character(slug: str, **query_params) -> Character:
    """Get a single character."""
    return get_characters().get(slug=slug, **query_params)


def get_character_version(**query_params) -> CharacterVersion:
    """Get a single character version."""
    return (
        CharacterVersion.objects.select_related('character', 'character__film')
        .prefetch_related(
            'static_asset',
            'static_asset__user',
            'static_asset__author',
            'character__likes',
            'comments',
            'comments__user',
        )
        .get(**query_params)
    )


def get_character_showcase(slug: str, pk: int) -> CharacterShowcase:
    """Get a character showcase."""
    return (
        CharacterShowcase.objects.select_related('character', 'character__film')
        .prefetch_related(
            'static_asset',
            'static_asset__user',
            'static_asset__author',
            'comments',
            'comments__user',
        )
        .get(character__slug=slug, pk=pk)
    )
