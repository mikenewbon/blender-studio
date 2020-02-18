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
    date_updated: datetime.datetime


@dc.dataclass
class Chapter:
    index: int
    name: str
    url: str


@dc.dataclass
class Section:
    index: int
    name: str
    text: str
    url: str


@dc.dataclass
class Video:
    url: str


@dc.dataclass
class Asset:
    name: str
    url: str


@dc.dataclass
class CommentTree:
    username: str
    date_updated: datetime.datetime
    message: str
    likes: int
    replies: List[CommentTree]
