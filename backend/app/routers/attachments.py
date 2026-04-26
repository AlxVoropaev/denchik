import mimetypes
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

# Whitelist of MIME types we accept on upload. Anything outside this set is
# rejected with 415 — both because the project doesn't need it, and because
# inline-renderable types like text/html or image/svg+xml on the app's own
# origin would let an attacker XSS by uploading + sharing a download link.
# `application/octet-stream` covers binary blobs whose precise type we don't
# care about (the download endpoint serves everything as octet-stream anyway).
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
    }
)

# Whitelist for storage-side extension. Anything that doesn't match is dropped
# rather than reflected onto disk, so a hostile filename can't shape the
# on-disk path (e.g. embed `/`, `..`, control chars, or a wildly long suffix).
_SAFE_EXT_RE = re.compile(r"^\.[A-Za-z0-9]{1,16}$")
# Allowed characters for the human-facing filename we keep in the DB and
# echo back via Content-Disposition. Anything else becomes `_`. This blocks
# CR/LF, slashes, backslashes, NULs, and other control bytes.
_UNSAFE_NAME_CHARS_RE = re.compile(r"[^A-Za-z0-9._\- ]")
_MAX_DISPLAY_FILENAME_LEN = 200


def _sanitize_display_filename(raw: str | None) -> str:
    """Return a filesystem-/header-safe version of a user-supplied filename.

    Strips path components, replaces unsafe characters with ``_``, caps length.
    Empty or all-junk input collapses to ``"file"``.
    """
    base = os.path.basename(raw or "")
    base = _UNSAFE_NAME_CHARS_RE.sub("_", base)
    base = base.strip(" .") or "file"
    return base[:_MAX_DISPLAY_FILENAME_LEN]


def _safe_extension(raw: str | None) -> str:
    """Extract a whitelisted extension from a user-supplied filename, or ``""``."""
    ext = os.path.splitext(os.path.basename(raw or ""))[1].lower()
    return ext if _SAFE_EXT_RE.match(ext) else ""

from app.core.config import get_settings
from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentOut
from app.services.workspace import get_task_with_workspace_id

router = APIRouter(tags=["attachments"])


@router.get("/tasks/{task_id}/attachments", response_model=list[AttachmentOut])
async def list_attachments(
    task_id: int, user: CurrentUser, session: SessionDep
) -> list[Attachment]:
    _, ws_id = await get_task_with_workspace_id(session, task_id)
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
    task, ws_id = await get_task_with_workspace_id(session, task_id)
    await require_workspace_member(ws_id, session, user)

    # Reject anything outside the whitelist before we touch the disk. The
    # client-supplied content_type isn't authoritative, but a mismatch here
    # is enough to block obvious abuses (text/html, image/svg+xml, etc.).
    declared_type = (file.content_type or "application/octet-stream").lower()
    if declared_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported file type"
        )

    # Cross-check against what the filename's extension implies. If the two
    # disagree on family (e.g. .html uploaded as image/png), fall back to a
    # safe generic type rather than trusting the client header.
    guessed, _ = mimetypes.guess_type(file.filename or "")
    if guessed and guessed.lower() != declared_type:
        declared_type = "application/octet-stream"

    data = await file.read()
    if len(data) > settings.max_attachment_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")

    Path(settings.attachments_dir).mkdir(parents=True, exist_ok=True)
    safe_display_name = _sanitize_display_filename(file.filename)
    storage_name = f"{uuid.uuid4().hex}{_safe_extension(file.filename)}"
    storage_path = os.path.join(settings.attachments_dir, storage_name)
    with open(storage_path, "wb") as f:
        f.write(data)

    att = Attachment(
        task_id=task.id,
        uploaded_by=user.id,
        filename=safe_display_name,
        content_type=declared_type,
        size=len(data),
        storage_path=storage_path,
    )
    session.add(att)
    # The on-disk write happened before the commit, so a commit failure (FK
    # violation, IntegrityError, etc.) would leave an orphaned blob. Unlink
    # the file before re-raising. NB: keep this try/except tightly scoped to
    # `commit()` — a later failure (e.g. from `refresh`) means the row is
    # already persisted and the file should NOT be removed.
    try:
        await session.commit()
    except Exception:
        try:
            os.unlink(storage_path)
        except OSError:
            pass
        raise
    await session.refresh(att)
    return att


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int, user: CurrentUser, session: SessionDep
) -> FileResponse:
    att = await session.get(Attachment, attachment_id)
    if att is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    _, ws_id = await get_task_with_workspace_id(session, att.task_id)
    await require_workspace_member(ws_id, session, user)
    # Always serve as a generic binary download, regardless of the stored
    # content_type. This neutralizes any user-uploaded HTML/SVG/JS that would
    # otherwise be rendered inline by the browser on the app's own origin —
    # the canonical "stored XSS via file upload" footgun. Starlette's
    # FileResponse already sets Content-Disposition: attachment when a
    # filename is provided.
    return FileResponse(
        att.storage_path,
        filename=att.filename,
        media_type="application/octet-stream",
    )
