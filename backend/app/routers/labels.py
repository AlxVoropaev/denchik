from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.label import Label
from app.schemas.label import LabelCreate, LabelOut

router = APIRouter(prefix="/labels", tags=["labels"])


@router.get("", response_model=list[LabelOut])
async def list_labels(
    workspace_id: int, user: CurrentUser, session: SessionDep
) -> list[Label]:
    await require_workspace_member(workspace_id, session, user)
    res = await session.execute(
        select(Label).where(Label.workspace_id == workspace_id).order_by(Label.id)
    )
    return list(res.scalars().all())


@router.post("", response_model=LabelOut, status_code=status.HTTP_201_CREATED)
async def create_label(
    payload: LabelCreate, user: CurrentUser, session: SessionDep
) -> Label:
    await require_workspace_member(payload.workspace_id, session, user)
    label = Label(workspace_id=payload.workspace_id, name=payload.name, color=payload.color)
    session.add(label)
    await session.commit()
    await session.refresh(label)
    return label
