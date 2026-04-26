import os
import tempfile
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Configure isolated test settings BEFORE importing the app.
_TMP = tempfile.mkdtemp(prefix="denchik-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["ATTACHMENTS_DIR"] = f"{_TMP}/attachments"
os.environ["JWT_SECRET"] = "test-secret"

from app.core.config import get_settings  # noqa: E402
from app.core.db import Base, get_engine, reset_engine_for_tests  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture
async def app():
    get_settings.cache_clear()
    reset_engine_for_tests()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    application = create_app()
    yield application
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Registered + logged in (cookie set on the client)."""
    resp = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "secretpw",
            "display_name": "Alice",
        },
    )
    assert resp.status_code == 201, resp.text
    return client


@pytest_asyncio.fixture
async def workspace(auth_client: AsyncClient) -> dict:
    resp = await auth_client.post("/workspaces", json={"name": "Acme"})
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def epic_group(auth_client: AsyncClient, workspace) -> dict:
    resp = await auth_client.post(
        "/epic-groups", json={"workspace_id": workspace["id"], "name": "Backlog"}
    )
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def epic(auth_client: AsyncClient, epic_group) -> dict:
    resp = await auth_client.post(
        "/epics", json={"epic_group_id": epic_group["id"], "name": "Auth"}
    )
    assert resp.status_code == 201
    return resp.json()
