from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.models.task import Task


async def next_task_position(session: AsyncSession, epic_id: int) -> int:
    res = await session.execute(
        select(func.coalesce(func.max(Task.position), -1)).where(Task.epic_id == epic_id)
    )
    return int(res.scalar_one()) + 1


async def next_epic_position(session: AsyncSession, group_id: int) -> int:
    res = await session.execute(
        select(func.coalesce(func.max(Epic.position), -1)).where(
            Epic.epic_group_id == group_id
        )
    )
    return int(res.scalar_one()) + 1


async def next_group_position(session: AsyncSession, workspace_id: int) -> int:
    res = await session.execute(
        select(func.coalesce(func.max(EpicGroup.position), -1)).where(
            EpicGroup.workspace_id == workspace_id
        )
    )
    return int(res.scalar_one()) + 1
