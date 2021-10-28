from django.urls import path

from characters.views.api.comment import comment_version, comment_showcase
from characters.views.api.like import character_like
from characters.views.characters import (
    CharacterList,
    CharacterDetail,
    CharacterVersionDetail,
    CharacterShowcaseDetail,
)


urlpatterns = [
    path(
        'api/characters/v/<int:character_version_pk>/comment/',
        comment_version,
        name='api-character-version-comment',
    ),
    path(
        'api/characters/showcase/<int:character_showcase_pk>/comment/',
        comment_showcase,
        name='api-character-showcase-comment',
    ),
    path('api/characters/<int:character_pk>/like/', character_like, name='api-character-like'),
    path('characters/', CharacterList.as_view(), name='character-list'),
    path('characters/<slug:slug>/', CharacterDetail.as_view(), name='character-detail'),
    path(
        'characters/<slug:slug>/v<int:number>/',
        CharacterVersionDetail.as_view(),
        name='character-version-detail',
    ),
    path(
        'characters/<slug:slug>/showcase/<int:pk>/',
        CharacterShowcaseDetail.as_view(),
        name='character-showcase-detail',
    ),
]
