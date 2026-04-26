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
