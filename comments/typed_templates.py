from __future__ import annotations

import dataclasses as dc
import datetime
from typing import List, Optional


@dc.dataclass
class Comments:
    comment_url: str
    number_of_comments: int
    comment_trees: List[CommentTree]
    profile_image_url: str


@dc.dataclass
class CommentTree:
    id: int
    username: str
    date: datetime.datetime
    message: str
    like_url: str
    liked: bool
    likes: int
    replies: List[CommentTree]
    profile_image_url: str
    edit_url: Optional[str]
    delete_url: Optional[str]
