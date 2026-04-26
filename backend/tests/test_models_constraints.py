"""Direct DB-level constraints (cascade etc.)."""
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.models.epic_group import EpicGroup
from app.models.task import Task


async def test_deleting_epic_group_cascades_to_epics_and_tasks(app, auth_client, epic, workspace):
    # Create a task to ensure cascade works
    await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "A"})
    sm = get_sessionmaker()
    async with sm() as s:
        groups = (await s.execute(select(EpicGroup))).scalars().all()
        for g in groups:
            await s.delete(g)
        await s.commit()
        remaining_tasks = (await s.execute(select(Task))).scalars().all()
        assert remaining_tasks == []
