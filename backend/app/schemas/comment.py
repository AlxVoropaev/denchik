from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    parent_comment_id: int | None = None


class CommentOut(BaseModel):
    id: int
    task_id: int
    parent_comment_id: int | None
    author_id: int
    body: str
    created_at: datetime
    edited_at: datetime | None

    model_config = {"from_attributes": True}
