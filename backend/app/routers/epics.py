from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.schemas.epic import EpicCreate, EpicOut, EpicUpdate
from app.services.positions import next_epic_position

router = APIRouter(prefix="/epics", tags=["epics"])


async def _epic_workspace_id(session, group_id: int) -> int:
    group = await session.get(EpicGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Epic group not found")
    return group.workspace_id


@router.get("", response_model=list[EpicOut])
async def list_epics(
    epic_group_id: int, user: CurrentUser, session: SessionDep
) -> list[Epic]:
    ws_id = await _epic_workspace_id(session, epic_group_id)
    await require_workspace_member(ws_id, session, user)
    res = await session.execute(
        select(Epic)
        .where(Epic.epic_group_id == epic_group_id)
        .order_by(Epic.position, Epic.id)
    )
    return list(res.scalars().all())


@router.post("", response_model=EpicOut, status_code=status.HTTP_201_CREATED)
async def create_epic(payload: EpicCreate, user: CurrentUser, session: SessionDep) -> Epic:
    ws_id = await _epic_workspace_id(session, payload.epic_group_id)
    await require_workspace_member(ws_id, session, user)
    pos = await next_epic_position(session, payload.epic_group_id)
    epic = Epic(epic_group_id=payload.epic_group_id, name=payload.name, position=pos)
    session.add(epic)
    await session.commit()
    await session.refresh(epic)
    return epic


@router.patch("/{epic_id}", response_model=EpicOut)
async def update_epic(
    epic_id: int, payload: EpicUpdate, user: CurrentUser, session: SessionDep
) -> Epic:
    epic = await session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    ws_id = await _epic_workspace_id(session, epic.epic_group_id)
    await require_workspace_member(ws_id, session, user)
    if payload.name is not None:
        epic.name = payload.name
    if payload.position is not None:
        epic.position = payload.position
    if payload.epic_group_id is not None:
        new_ws = await _epic_workspace_id(session, payload.epic_group_id)
        await require_workspace_member(new_ws, session, user)
        epic.epic_group_id = payload.epic_group_id
    await session.commit()
    await session.refresh(epic)
    return epic


@router.delete("/{epic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_epic(epic_id: int, user: CurrentUser, session: SessionDep) -> None:
    epic = await session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    ws_id = await _epic_workspace_id(session, epic.epic_group_id)
    await require_workspace_member(ws_id, session, user)
    await session.delete(epic)
    await session.commit()
