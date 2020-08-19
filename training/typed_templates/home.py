import dataclasses as dc
from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from common.typed_templates.types import TypeSafeTemplateResponse
from training.typed_templates.types import Training


@dc.dataclass
class RecentlyWatchedSection:
    index: int
    name: str
    url: str
    training_name: str
    chapter_index: int
    chapter_name: str
    progress_fraction: float

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'

    @property
    def chapter_name_with_index(self) -> str:
        return f'{self.chapter_index:02.0f}. {self.chapter_name}'


def home_authenticated(
    request: HttpRequest,
    *,
    recently_watched_sections: Sequence[RecentlyWatchedSection],
    favorited_trainings: Sequence[Training],
    all_trainings: Sequence[Training],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training/home_authenticated.html',
            context={
                'recently_watched_sections': recently_watched_sections,
                'favorited_trainings': favorited_trainings,
                'all_trainings': all_trainings,
            },
        )
    )


def home_not_authenticated(
    request: HttpRequest, *, all_trainings: Sequence[Training],
) -> TypeSafeTemplateResponse:
    return TypeSafeTemplateResponse(
        TemplateResponse(
            request,
            'training/home_not_authenticated.html',
            context={'all_trainings': all_trainings},
        )
    )
