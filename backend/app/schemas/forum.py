from datetime import datetime

from pydantic import BaseModel


class ForumTopic(BaseModel):
    """A task as a forum topic."""

    task_id: int
    title: str
    author_id: int
    created_at: datetime
    updated_at: datetime
    comment_count: int
    last_comment_author_id: int | None
    last_comment_at: datetime | None


class ForumSubforum(BaseModel):
    """An epic as a subforum."""

    epic_id: int
    name: str
    position: int
    topics: list[ForumTopic]


class ForumView(BaseModel):
    """An epic group as a forum."""

    epic_group_id: int
    name: str
    subforums: list[ForumSubforum]
