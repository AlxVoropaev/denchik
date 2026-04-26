import io

import pytest_asyncio


@pytest_asyncio.fixture
async def task(auth_client, epic):
    r = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "T"})
    return r.json()


async def test_upload_and_download_attachment(auth_client, task):
    files = {"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")}
    r = await auth_client.post(f"/tasks/{task['id']}/attachments", files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "hello.txt"
    assert body["size"] == len(b"hello world")

    dl = await auth_client.get(f"/attachments/{body['id']}/download")
    assert dl.status_code == 200
    assert dl.content == b"hello world"


async def test_attachment_too_large_rejected(auth_client, task, monkeypatch):
    from app.core.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "max_attachment_bytes", 5)
    files = {"file": ("big.bin", io.BytesIO(b"x" * 100), "application/octet-stream")}
    r = await auth_client.post(f"/tasks/{task['id']}/attachments", files=files)
    assert r.status_code == 413


async def test_attachment_deleted_with_task(auth_client, task):
    files = {"file": ("a.txt", io.BytesIO(b"a"), "text/plain")}
    up = await auth_client.post(f"/tasks/{task['id']}/attachments", files=files)
    aid = up.json()["id"]
    await auth_client.delete(f"/tasks/{task['id']}")
    dl = await auth_client.get(f"/attachments/{aid}/download")
    assert dl.status_code == 404


async def test_attachment_filename_path_traversal_is_neutralized(auth_client, task):
    """A malicious filename like ``../../etc/pwned.txt`` must not escape the
    configured attachments directory, and the DB-stored filename must be
    sanitized (no slashes, no special chars beyond [A-Za-z0-9._\\- ])."""
    import os as _os
    from pathlib import Path as _Path

    from app.core.config import get_settings
    from app.models.attachment import Attachment as _Attachment
    from app.core.db import get_sessionmaker
    from sqlalchemy import select as _select

    settings = get_settings()
    attachments_dir = _Path(settings.attachments_dir).resolve()

    files = {
        "file": (
            "../../etc/pwned.txt",
            io.BytesIO(b"payload"),
            "text/plain",
        )
    }
    r = await auth_client.post(f"/tasks/{task['id']}/attachments", files=files)
    assert r.status_code == 201, r.text
    body = r.json()

    # DB filename (used for Content-Disposition) must be sanitized: no slashes,
    # no `..` traversal segments.
    assert "/" not in body["filename"]
    assert "\\" not in body["filename"]
    assert ".." not in body["filename"]

    # Look up the row to inspect storage_path on disk.
    async with get_sessionmaker()() as session:
        res = await session.execute(
            _select(_Attachment).where(_Attachment.id == body["id"])
        )
        att = res.scalar_one()

    storage_path = _Path(att.storage_path).resolve()
    # File must be physically inside the attachments dir (no traversal escape).
    assert str(storage_path).startswith(str(attachments_dir) + _os.sep), (
        f"storage_path {storage_path} escaped attachments dir {attachments_dir}"
    )
    # On-disk basename must NOT contain any path separators or `..`.
    base = _os.path.basename(att.storage_path)
    assert "/" not in base and "\\" not in base
    assert ".." not in base
    # File must actually exist where we expect.
    assert storage_path.is_file()


async def test_upload_does_not_orphan_file_on_commit_failure(
    auth_client, task, monkeypatch
):
    """If the DB commit fails after the file has already been written, the
    on-disk file must be unlinked so we don't leak orphaned blobs in the
    attachments dir. After unhooking the failure, a subsequent successful
    upload must result in exactly one file being present."""
    import os as _os
    from pathlib import Path as _Path

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.config import get_settings

    settings = get_settings()
    attachments_dir = _Path(settings.attachments_dir)
    attachments_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot whatever was already written by earlier fixtures (none here,
    # but be defensive) so we count only new files.
    pre_existing = {
        p.name for p in attachments_dir.iterdir() if p.is_file()
    }

    # Patch AsyncSession.commit to raise the first time it's called from
    # within the upload handler. We restore it before doing the second
    # (successful) upload.
    original_commit = AsyncSession.commit

    async def boom_commit(self):  # type: ignore[no-untyped-def]
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(AsyncSession, "commit", boom_commit)

    # httpx's ASGITransport propagates app-level exceptions by default, so we
    # expect the forced RuntimeError to bubble out of the request call.
    import pytest as _pytest

    files = {"file": ("oops.txt", io.BytesIO(b"orphan?"), "text/plain")}
    with _pytest.raises(RuntimeError, match="forced commit failure"):
        await auth_client.post(
            f"/tasks/{task['id']}/attachments", files=files
        )

    new_files_after_failure = {
        p.name for p in attachments_dir.iterdir() if p.is_file()
    } - pre_existing
    assert new_files_after_failure == set(), (
        f"commit failure left orphaned file(s): {new_files_after_failure}"
    )

    # Restore commit and verify a clean upload now produces exactly one file.
    monkeypatch.setattr(AsyncSession, "commit", original_commit)

    files = {"file": ("ok.txt", io.BytesIO(b"good"), "text/plain")}
    r2 = await auth_client.post(
        f"/tasks/{task['id']}/attachments", files=files
    )
    assert r2.status_code == 201, r2.text

    new_files_after_success = {
        p.name for p in attachments_dir.iterdir() if p.is_file()
    } - pre_existing
    assert len(new_files_after_success) == 1, (
        f"expected exactly one new file after successful upload, "
        f"got: {new_files_after_success}"
    )


async def test_attachment_extension_whitelisted_and_name_sanitized(auth_client, task):
    """`.exe` is a normal extension and must survive on the storage filename.
    A nasty name with `#`, `/`, `..` must be sanitized in the DB filename."""
    import os as _os
    from pathlib import Path as _Path

    from app.core.config import get_settings

    settings = get_settings()
    attachments_dir = _Path(settings.attachments_dir).resolve()

    # .exe extension preserved on storage filename
    r1 = await auth_client.post(
        f"/tasks/{task['id']}/attachments",
        files={"file": ("installer.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert r1.status_code == 201, r1.text

    from app.models.attachment import Attachment as _Attachment
    from app.core.db import get_sessionmaker
    from sqlalchemy import select as _select

    async with get_sessionmaker()() as session:
        res = await session.execute(
            _select(_Attachment).where(_Attachment.id == r1.json()["id"])
        )
        att1 = res.scalar_one()
    assert att1.storage_path.endswith(".exe"), att1.storage_path
    assert _Path(att1.storage_path).resolve().is_file()

    # Sanitization of nasty name: `Pas#word/../foo.txt`
    r2 = await auth_client.post(
        f"/tasks/{task['id']}/attachments",
        files={"file": ("Pas#word/../foo.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r2.status_code == 201, r2.text
    body2 = r2.json()
    # DB-stored display filename has no `/`, no `..`, and `#` is replaced.
    assert "/" not in body2["filename"]
    assert ".." not in body2["filename"]
    assert "#" not in body2["filename"]

    async with get_sessionmaker()() as session:
        res = await session.execute(
            _select(_Attachment).where(_Attachment.id == body2["id"])
        )
        att2 = res.scalar_one()
    storage_path = _Path(att2.storage_path).resolve()
    assert str(storage_path).startswith(str(attachments_dir) + _os.sep)
    base = _os.path.basename(att2.storage_path)
    assert "/" not in base and ".." not in base
