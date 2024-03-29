from __future__ import annotations

from typing import List, Optional, Set, TypedDict
import dataclasses as dc
import datetime

from django.db.models.manager import Manager
from markupsafe import Markup

from training.models import trainings


@dc.dataclass
class Training:
    id: int
    name: str
    description: str
    summary: Markup
    type: trainings.TrainingType
    difficulty: trainings.TrainingDifficulty
    tags: Set[str]
    url: str
    admin_url: str
    favorite_url: str
    date_updated: datetime.datetime
    favorited: bool
    thumbnail: str
    thumbnail_s_url: str
    thumbnail_m_url: str
    picture_header: str
    is_free: bool
    flatpages: Manager[trainings.TrainingFlatPage]


@dc.dataclass
class Chapter:
    index: int
    name: str
    is_published: bool

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'


@dc.dataclass
class Video:
    url: str
    progress_url: str
    start_position: Optional[float]


@dc.dataclass
class Navigation:
    training_admin_url: Optional[str]

    overview_url: str
    overview_active: bool

    chapters: List[ChapterNavigation]


@dc.dataclass
class ChapterNavigation:
    index: int
    name: str
    slug: str
    current: bool
    is_published: bool

    admin_url: Optional[str]
    url: Optional[str]

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
    is_free: bool
    is_featured: bool
    is_published: bool
    source_type: str

    admin_url: Optional[str]

    @property
    def name_with_index(self) -> str:
        return f'{self.index:02.0f}. {self.name}'


class SectionProgressReportingData(TypedDict):
    progress_url: str
    started_timeout: Optional[float]
    finished_timeout: Optional[float]
