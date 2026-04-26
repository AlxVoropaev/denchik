from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.models.label import Label, TaskLabel
from app.models.task import Task
from app.schemas.task import TaskOut, TaskQuickCreate, TaskUpdate
from app.services.positions import next_task_position

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _task_workspace_id(session, epic_id: int) -> int:
    epic = await session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Epic not found")
    group = await session.get(EpicGroup, epic.epic_group_id)
    assert group is not None
    return group.workspace_id


async def _load_task(session, task_id: int) -> Task:
    res = await session.execute(
        select(Task).options(selectinload(Task.labels)).where(Task.id == task_id)
    )
    task = res.scalar_one_or_none()
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


async def _attach_labels(session, task: Task, label_ids: list[int]) -> None:
    """Replace the task's labels via the join table (avoids async lazy-load)."""
    await session.execute(delete(TaskLabel).where(TaskLabel.task_id == task.id))
    if not label_ids:
        return
    res = await session.execute(select(Label.id).where(Label.id.in_(label_ids)))
    valid_ids = list(res.scalars().all())
    if valid_ids:
        await session.execute(
            insert(TaskLabel),
            [{"task_id": task.id, "label_id": lid} for lid in valid_ids],
        )


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    epic_id: int, user: CurrentUser, session: SessionDep
) -> list[Task]:
    ws_id = await _task_workspace_id(session, epic_id)
    await require_workspace_member(ws_id, session, user)
    res = await session.execute(
        select(Task)
        .options(selectinload(Task.labels))
        .where(Task.epic_id == epic_id)
        .order_by(Task.position, Task.id)
    )
    return list(res.scalars().all())


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskQuickCreate, user: CurrentUser, session: SessionDep
) -> Task:
    ws_id = await _task_workspace_id(session, payload.epic_id)
    await require_workspace_member(ws_id, session, user)
    pos = await next_task_position(session, payload.epic_id)
    task = Task(
        epic_id=payload.epic_id,
        author_id=user.id,
        title=payload.title,
        description=payload.description,
        position=pos,
    )
    if payload.status is not None:
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.assignee_id is not None:
        task.assignee_id = payload.assignee_id
    if payload.due_date is not None:
        task.due_date = payload.due_date
    session.add(task)
    await session.flush()
    if payload.label_ids is not None:
        await _attach_labels(session, task, payload.label_ids)
    await session.commit()
    return await _load_task(session, task.id)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user: CurrentUser, session: SessionDep) -> Task:
    task = await _load_task(session, task_id)
    ws_id = await _task_workspace_id(session, task.epic_id)
    await require_workspace_member(ws_id, session, user)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, user: CurrentUser, session: SessionDep
) -> Task:
    task = await _load_task(session, task_id)
    ws_id = await _task_workspace_id(session, task.epic_id)
    await require_workspace_member(ws_id, session, user)

    data = payload.model_dump(exclude_unset=True)
    label_ids = data.pop("label_ids", None)
    if "epic_id" in data and data["epic_id"] != task.epic_id:
        new_ws = await _task_workspace_id(session, data["epic_id"])
        await require_workspace_member(new_ws, session, user)
    for field, value in data.items():
        setattr(task, field, value)
    if label_ids is not None:
        await _attach_labels(session, task, label_ids)
    await session.commit()
    return await _load_task(session, task.id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: CurrentUser, session: SessionDep) -> None:
    task = await _load_task(session, task_id)
    ws_id = await _task_workspace_id(session, task.epic_id)
    await require_workspace_member(ws_id, session, user)
    await session.delete(task)
    await session.commit()
