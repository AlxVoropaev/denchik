"""Regression tests for review item #15.

Several router helpers used ``assert obj is not None`` after
``session.get(...)`` calls that walk Task -> Epic -> EpicGroup. With
``python -O`` those asserts are stripped and the next attribute access on
``None`` raises ``AttributeError`` (HTTP 500). We want a proper 404 instead.

We can't easily run pytest under ``-O``, so we simulate the bug's real
trigger: an orphaned row. SQLite has FK enforcement off by default in this
project, so we DELETE the parent row directly, leaving the child task
intact, and assert the endpoint replies 404 (not 500).

Each test exercises a different helper:

* ``backend/app/routers/tasks.py::_task_workspace_id``
* ``backend/app/routers/comments.py::_ws_for_task``
* ``backend/app/routers/attachments.py::_ws_for_task``
"""

import io

import pytest_asyncio
from sqlalchemy import delete

from app.core.db import get_sessionmaker
from app.models.epic import Epic
from app.models.epic_group import EpicGroup


@pytest_asyncio.fixture
async def task(auth_client, epic):
    r = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "T"})
    return r.json()


async def _orphan_task_from_epic_group(task_id: int) -> None:
    """Delete the EpicGroup row that the task ultimately hangs off of,
    leaving the Epic and Task rows behind. SQLite FK enforcement is off, so
    the rows survive — the join through Epic -> EpicGroup just returns None.
    """
    async with get_sessionmaker()() as session:
        # find the epic_group id via the task -> epic chain
        from app.models.task import Task as _Task

        t = await session.get(_Task, task_id)
        assert t is not None
        e = await session.get(Epic, t.epic_id)
        assert e is not None
        await session.execute(delete(EpicGroup).where(EpicGroup.id == e.epic_group_id))
        await session.commit()


async def _orphan_task_from_epic(task_id: int) -> None:
    """Delete the Epic row but leave the Task row behind. Forces
    ``session.get(Epic, task.epic_id)`` to return None inside the helpers
    in comments.py / attachments.py.
    """
    async with get_sessionmaker()() as session:
        from app.models.task import Task as _Task

        t = await session.get(_Task, task_id)
        assert t is not None
        await session.execute(delete(Epic).where(Epic.id == t.epic_id))
        await session.commit()


# ---------------------------------------------------------------------------
# tasks router: _task_workspace_id
# ---------------------------------------------------------------------------


async def test_list_tasks_returns_404_when_epic_group_is_missing(
    auth_client, epic, task
):
    """Hits ``_task_workspace_id`` via GET /tasks?epic_id=..."""
    await _orphan_task_from_epic_group(task["id"])
    r = await auth_client.get(f"/tasks?epic_id={epic['id']}")
    assert r.status_code == 404, r.text


async def test_create_task_returns_404_when_epic_group_is_missing(
    auth_client, epic, task
):
    """Hits ``_task_workspace_id`` via POST /tasks."""
    await _orphan_task_from_epic_group(task["id"])
    r = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "X"})
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# comments router: _ws_for_task
# ---------------------------------------------------------------------------


async def test_list_comments_returns_404_when_epic_is_missing(auth_client, task):
    """Epic gone -> ``session.get(Epic, ...)`` returns None inside the helper."""
    await _orphan_task_from_epic(task["id"])
    r = await auth_client.get(f"/tasks/{task['id']}/comments")
    assert r.status_code == 404, r.text


async def test_list_comments_returns_404_when_epic_group_is_missing(auth_client, task):
    """Epic still there but EpicGroup gone -> second ``session.get`` returns None."""
    await _orphan_task_from_epic_group(task["id"])
    r = await auth_client.get(f"/tasks/{task['id']}/comments")
    assert r.status_code == 404, r.text


async def test_create_comment_returns_404_when_epic_group_is_missing(
    auth_client, task
):
    await _orphan_task_from_epic_group(task["id"])
    r = await auth_client.post(
        f"/tasks/{task['id']}/comments", json={"body": "hi"}
    )
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# attachments router: _ws_for_task
# ---------------------------------------------------------------------------


async def test_list_attachments_returns_404_when_epic_is_missing(auth_client, task):
    await _orphan_task_from_epic(task["id"])
    r = await auth_client.get(f"/tasks/{task['id']}/attachments")
    assert r.status_code == 404, r.text


async def test_list_attachments_returns_404_when_epic_group_is_missing(
    auth_client, task
):
    await _orphan_task_from_epic_group(task["id"])
    r = await auth_client.get(f"/tasks/{task['id']}/attachments")
    assert r.status_code == 404, r.text


async def test_upload_attachment_returns_404_when_epic_group_is_missing(
    auth_client, task
):
    await _orphan_task_from_epic_group(task["id"])
    files = {"file": ("hi.txt", io.BytesIO(b"x"), "text/plain")}
    r = await auth_client.post(f"/tasks/{task['id']}/attachments", files=files)
    assert r.status_code == 404, r.text
