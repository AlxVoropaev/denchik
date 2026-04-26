import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.attachment import Attachment
from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.models.task import Task
from app.schemas.attachment import AttachmentOut

router = APIRouter(tags=["attachments"])


async def _ws_for_task(session, task_id: int) -> tuple[Task, int]:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    epic = await session.get(Epic, task.epic_id)
    assert epic is not None
    group = await session.get(EpicGroup, epic.epic_group_id)
    assert group is not None
    return task, group.workspace_id


@router.get("/tasks/{task_id}/attachments", response_model=list[AttachmentOut])
async def list_attachments(
    task_id: int, user: CurrentUser, session: SessionDep
) -> list[Attachment]:
    _, ws_id = await _ws_for_task(session, task_id)
    await require_workspace_member(ws_id, session, user)
    res = await session.execute(
        select(Attachment).where(Attachment.task_id == task_id).order_by(Attachment.id)
    )
    return list(res.scalars().all())


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    task_id: int, file: UploadFile, user: CurrentUser, session: SessionDep
) -> Attachment:
    settings = get_settings()
    task, ws_id = await _ws_for_task(session, task_id)
    await require_workspace_member(ws_id, session, user)

    data = await file.read()
    if len(data) > settings.max_attachment_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")

    Path(settings.attachments_dir).mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid.uuid4().hex}_{file.filename}"
    storage_path = os.path.join(settings.attachments_dir, storage_name)
    with open(storage_path, "wb") as f:
        f.write(data)

    att = Attachment(
        task_id=task.id,
        uploaded_by=user.id,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size=len(data),
        storage_path=storage_path,
    )
    session.add(att)
    await session.commit()
    await session.refresh(att)
    return att


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int, user: CurrentUser, session: SessionDep
) -> FileResponse:
    att = await session.get(Attachment, attachment_id)
    if att is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    _, ws_id = await _ws_for_task(session, att.task_id)
    await require_workspace_member(ws_id, session, user)
    return FileResponse(att.storage_path, filename=att.filename, media_type=att.content_type)
