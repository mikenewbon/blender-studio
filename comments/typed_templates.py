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
    replies: List[CommentTree]
    profile_image_url: str
    is_archived: bool
    is_top_level: bool
    full_name: str
    message: str
    like_url: Optional[str]
    liked: bool
    likes: int
    edit_url: Optional[str]
    admin_edit_url: Optional[str]
    delete_url: Optional[str]
    admin_delete_url: Optional[str]
    delete_tree_url: Optional[str]
    hard_delete_tree_url: Optional[str]
    edited: bool


@dc.dataclass
class DeletedCommentTree(CommentTree):
    full_name: Literal['[deleted]'] = '[deleted]'
    message: Literal['[deleted]'] = '[deleted]'
    like_url: Literal[None] = None
    liked: Literal[False] = False
    likes: Literal[0] = 0
    edit_url: Literal[None] = None
    admin_edit_url: Literal[None] = None
    delete_url: Literal[None] = None
    admin_delete_url: Literal[None] = None
    delete_tree_url: Literal[None] = None
    hard_delete_tree_url: Literal[None] = None
    edited: Literal[False] = False
    is_deleted: Literal[True] = True
