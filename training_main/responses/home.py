import dataclasses as dc
from typing import Sequence

from django.http.request import HttpRequest
from django.template.response import TemplateResponse

from training_main.responses.common import Training, Section
from training_main.responses.types import TypeSafeTemplateResponse


@dc.dataclass
class RecentlyWatchedSection(Section):
    training_name: str
    chapter_index: int
    chapter_name: str
    progress_fraction: float

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
            'training_main/home_authenticated.html',
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
            'training_main/home_not_authenticated.html',
            context={'all_trainings': all_trainings},
        )
    )
