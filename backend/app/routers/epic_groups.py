from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.epic_group import EpicGroup
from app.schemas.epic import EpicGroupCreate, EpicGroupOut
from app.services.positions import next_group_position

router = APIRouter(prefix="/epic-groups", tags=["epic-groups"])


@router.get("", response_model=list[EpicGroupOut])
async def list_groups(workspace_id: int, user: CurrentUser, session: SessionDep) -> list[EpicGroup]:
    await require_workspace_member(workspace_id, session, user)
    res = await session.execute(
        select(EpicGroup)
        .where(EpicGroup.workspace_id == workspace_id)
        .order_by(EpicGroup.position, EpicGroup.id)
    )
    return list(res.scalars().all())


@router.post("", response_model=EpicGroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: EpicGroupCreate, user: CurrentUser, session: SessionDep
) -> EpicGroup:
    await require_workspace_member(payload.workspace_id, session, user)
    pos = await next_group_position(session, payload.workspace_id)
    group = EpicGroup(workspace_id=payload.workspace_id, name=payload.name, position=pos)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: int, user: CurrentUser, session: SessionDep) -> None:
    group = await session.get(EpicGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    await require_workspace_member(group.workspace_id, session, user)
    await session.delete(group)
    await session.commit()
