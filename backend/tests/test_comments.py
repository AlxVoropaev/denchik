import pytest_asyncio


@pytest_asyncio.fixture
async def task(auth_client, epic):
    r = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "T"})
    return r.json()


async def test_create_top_level_comment(auth_client, task):
    r = await auth_client.post(
        f"/tasks/{task['id']}/comments", json={"body": "First comment"}
    )
    assert r.status_code == 201
    assert r.json()["parent_comment_id"] is None


async def test_reply_to_comment(auth_client, task):
    p = (
        await auth_client.post(
            f"/tasks/{task['id']}/comments", json={"body": "Parent"}
        )
    ).json()
    r = await auth_client.post(
        f"/tasks/{task['id']}/comments",
        json={"body": "Reply", "parent_comment_id": p["id"]},
    )
    assert r.status_code == 201
    assert r.json()["parent_comment_id"] == p["id"]


async def test_cannot_nest_more_than_two_levels(auth_client, task):
    p = (
        await auth_client.post(
            f"/tasks/{task['id']}/comments", json={"body": "L0"}
        )
    ).json()
    c = (
        await auth_client.post(
            f"/tasks/{task['id']}/comments",
            json={"body": "L1", "parent_comment_id": p["id"]},
        )
    ).json()
    r = await auth_client.post(
        f"/tasks/{task['id']}/comments",
        json={"body": "L2", "parent_comment_id": c["id"]},
    )
    assert r.status_code == 400


async def test_list_comments(auth_client, task):
    await auth_client.post(f"/tasks/{task['id']}/comments", json={"body": "A"})
    await auth_client.post(f"/tasks/{task['id']}/comments", json={"body": "B"})
    r = await auth_client.get(f"/tasks/{task['id']}/comments")
    assert r.status_code == 200
    assert len(r.json()) == 2
