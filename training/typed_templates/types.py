from __future__ import annotations

import dataclasses as dc
import datetime
from typing import List, Optional, Set, TypedDict

from training.models import trainings


@dc.dataclass
class Training:
    name: str
    description: str
    summary: str
    type: trainings.TrainingType
    difficulty: trainings.TrainingDifficulty
    tags: Set[str]
    url: str
    favorite_url: str
    date_updated: datetime.datetime
    favorited: bool


@dc.dataclass
class Chapter:
    index: int
    name: str

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'


@dc.dataclass
class Section:
    index: int
    name: str
    text: str
    url: str

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'


@dc.dataclass
class Video:
    url: str
    progress_url: str
    start_position: Optional[float]


@dc.dataclass
class Asset:
    name: str
    url: str


@dc.dataclass
class Navigation:
    overview_url: str
    overview_active: bool

    chapters: List[ChapterNavigation]


@dc.dataclass
class ChapterNavigation:
    index: int
    name: str
    slug: str
    current: bool

    sections: List[SectionNavigation]

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'


@dc.dataclass
class SectionNavigation:
    index: int
    name: str
    url: str
    started: bool
    finished: bool
    progress_fraction: float
    current: bool

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'


class SectionProgressReportingData(TypedDict):
    progress_url: str
    started_timeout: Optional[float]
    finished_timeout: Optional[float]
