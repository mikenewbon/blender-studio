"""Describe authentication-related data types, used in templates."""
from __future__ import annotations

from typing import List, Dict
import dataclasses as dc
import datetime


@dc.dataclass
class User:
    """Describe User type."""

    is_anonymous: bool
    is_authenticated: bool

    full_name: str = None
    image_url: str = None
    username: str = None
    groups: List[Group] = None
    badges: Dict[Dict] = None

    is_active: bool = None
    is_staff: bool = None
    is_superuser: bool = None
    last_login: datetime.datetime = None
    date_joined: datetime.datetime = None


@dc.dataclass
class Group:
    """Describe Group type."""

    name: str
