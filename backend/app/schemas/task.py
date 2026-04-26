from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus


class TaskQuickCreate(BaseModel):
    """Minimum-action create: epic_id + title is enough."""

    epic_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    label_ids: list[int] | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    due_date: datetime | None = None
    epic_id: int | None = None
    position: int | None = None
    label_ids: list[int] | None = None


class LabelOut(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: int
    epic_id: int
    author_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: int | None
    due_date: datetime | None
    position: int
    created_at: datetime
    updated_at: datetime
    labels: list[LabelOut] = []

    model_config = {"from_attributes": True}
