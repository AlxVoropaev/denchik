from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import decode_token
from app.models.user import User
from app.models.workspace import WorkspaceMember


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    denchik_session: Annotated[str | None, Cookie()] = None,
) -> User:
    if not denchik_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(denchik_session)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    user_id = int(payload.get("sub", 0))
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def require_workspace_member(
    workspace_id: int, session: AsyncSession, user: User
) -> None:
    if workspace_id <= 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    res = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this workspace")


def get_settings_dep():
    return get_settings()
