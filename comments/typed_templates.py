from __future__ import annotations

import dataclasses as dc
import datetime
from typing import List, Optional, Literal, Union


@dc.dataclass
class Comments:
    comment_url: str
    number_of_comments: int
    comment_trees: List[CommentTree]
    profile_image_url: str


@dc.dataclass
class CommentTree:
    id: int
    date: datetime.datetime
    replies: List[Union[CommentTree, DeletedCommentTree]]
    profile_image_url: str
    full_name: str
    message: str
    like_url: Optional[str]
    liked: bool
    likes: int
    edit_url: Optional[str]
    delete_url: Optional[str]
    edited: bool = False


@dc.dataclass
class DeletedCommentTree(CommentTree):
    full_name: Literal['[deleted]'] = '[deleted]'
    message: Literal['[deleted]'] = '[deleted]'
    like_url: Literal[None] = None
    liked: Literal[False] = False
    likes: Literal[0] = 0
    edit_url: Literal[None] = None
    delete_url: Literal[None] = None
    is_deleted: Literal[True] = True
