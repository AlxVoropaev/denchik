from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.models.task import Task


async def get_task_with_workspace_id(
    session: AsyncSession, task_id: int
) -> tuple[Task, int]:
    """Load a task and the id of the workspace it ultimately belongs to.

    Walks ``Task -> Epic -> EpicGroup`` to find ``workspace_id``. Raises 404
    if any link in the chain is missing — FKs normally guarantee parents
    exist, but ``assert`` would silently vanish under ``python -O`` and the
    next attribute access would 500, so be explicit.

    Used by routers that need to gate access via ``require_workspace_member``
    but do not also need eager-loaded labels (the heavier ``_load_task``
    lives in ``routers/tasks.py``).
    """
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    epic = await session.get(Epic, task.epic_id)
    if epic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Epic not found")
    group = await session.get(EpicGroup, epic.epic_group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Epic group not found")
    return task, group.workspace_id
