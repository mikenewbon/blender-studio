from __future__ import annotations

import dataclasses as dc
import datetime
from typing import Set, List

from training_main.models import trainings


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
    url: str

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


@dc.dataclass
class Asset:
    name: str
    url: str


@dc.dataclass
class Comments:
    number_of_comments: int
    comment_trees: List[CommentTree]


@dc.dataclass
class CommentTree:
    username: str
    date_created: datetime.datetime
    message: str
    likes: int
    replies: List[CommentTree]
