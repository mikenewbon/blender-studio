"""Describe authentication and Profile related data types, used in templates."""
from __future__ import annotations

from typing import List
import dataclasses as dc
import datetime


@dc.dataclass
class User:
    """Describe User type."""

    is_anonymous: bool
    is_authenticated: bool

    username: str = None
    groups: List[Group] = None
    profile: Profile = None

    is_active: bool = None
    is_staff: bool = None
    is_superuser: bool = None
    last_login: datetime.datetime = None
    date_joined: datetime.datetime = None


@dc.dataclass
class Group:
    """Describe Group type."""

    name: str


@dc.dataclass
class Profile:
    """Describe Profile type."""

    full_name: str
    avatar_url: str
