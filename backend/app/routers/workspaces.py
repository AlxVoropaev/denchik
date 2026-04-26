from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import MemberAdd, WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: CurrentUser, session: SessionDep) -> list[Workspace]:
    res = await session.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.id)
    )
    return list(res.scalars().all())


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, user: CurrentUser, session: SessionDep
) -> Workspace:
    ws = Workspace(name=payload.name, owner_id=user.id)
    session.add(ws)
    await session.flush()
    session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.owner)
    )
    await session.commit()
    await session.refresh(ws)
    return ws


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: int, payload: MemberAdd, user: CurrentUser, session: SessionDep
) -> dict[str, int]:
    await require_workspace_member(workspace_id, session, user)
    target = await session.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    role = WorkspaceRole(payload.role) if payload.role in {"owner", "member"} else WorkspaceRole.member
    member = WorkspaceMember(
        workspace_id=workspace_id, user_id=payload.user_id, role=role
    )
    session.add(member)
    await session.commit()
    return {"id": member.id}
