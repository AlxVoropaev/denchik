from sqlalchemy import event

from app.core.db import get_engine


async def test_forum_view_structure(auth_client, workspace, epic_group, epic):
    # Create a second epic ("subforum") in the same group
    epic2 = (
        await auth_client.post(
            "/epics", json={"epic_group_id": epic_group["id"], "name": "Billing"}
        )
    ).json()

    # Two tasks in epic 1, one task in epic 2
    t1 = (
        await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "Login bug"})
    ).json()
    await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "Reset PW"})
    await auth_client.post("/tasks", json={"epic_id": epic2["id"], "title": "Invoice fix"})

    # Add a couple of comments to t1
    await auth_client.post(f"/tasks/{t1['id']}/comments", json={"body": "Anyone owns this?"})
    await auth_client.post(f"/tasks/{t1['id']}/comments", json={"body": "I'll take it."})

    r = await auth_client.get(f"/forum/{epic_group['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["epic_group_id"] == epic_group["id"]
    assert body["name"] == epic_group["name"]
    assert len(body["subforums"]) == 2

    sub1 = next(s for s in body["subforums"] if s["epic_id"] == epic["id"])
    assert len(sub1["topics"]) == 2
    topic1 = next(t for t in sub1["topics"] if t["task_id"] == t1["id"])
    assert topic1["comment_count"] == 2
    assert topic1["last_comment_at"] is not None


async def test_forum_view_empty_group(auth_client, epic_group):
    r = await auth_client.get(f"/forum/{epic_group['id']}")
    assert r.status_code == 200
    assert r.json()["subforums"] == []


async def test_forum_view_aggregates_in_constant_queries(
    auth_client, workspace, epic_group, epic
):
    """The forum aggregate must not do per-task or per-epic round-trips.

    Builds 2 epics * 3 tasks with 2 comments on one task, then asserts the
    response contains the expected counts and that the SQL workload for
    `GET /forum/{id}` stays bounded regardless of size.
    """
    epic2 = (
        await auth_client.post(
            "/epics", json={"epic_group_id": epic_group["id"], "name": "Reports"}
        )
    ).json()

    tasks_e1 = []
    for title in ("E1-T1", "E1-T2", "E1-T3"):
        r = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": title})
        tasks_e1.append(r.json())
    tasks_e2 = []
    for title in ("E2-T1", "E2-T2", "E2-T3"):
        r = await auth_client.post("/tasks", json={"epic_id": epic2["id"], "title": title})
        tasks_e2.append(r.json())

    # Two comments on one task in epic 1.
    chatty = tasks_e1[0]
    await auth_client.post(f"/tasks/{chatty['id']}/comments", json={"body": "first"})
    await auth_client.post(f"/tasks/{chatty['id']}/comments", json={"body": "second"})

    # Count SQL statements emitted while serving the forum endpoint.
    engine = get_engine()
    statements: list[str] = []

    def _on_exec(conn, cursor, statement, parameters, context, executemany):
        # Skip transaction bookkeeping; count only real DML/SELECTs.
        s = statement.strip().upper()
        if s.startswith(("BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "PRAGMA")):
            return
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _on_exec)
    try:
        r = await auth_client.get(f"/forum/{epic_group['id']}")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _on_exec)

    assert r.status_code == 200
    body = r.json()

    # Response shape sanity (unchanged by the optimisation).
    assert body["epic_group_id"] == epic_group["id"]
    assert len(body["subforums"]) == 2
    sub1 = next(s for s in body["subforums"] if s["epic_id"] == epic["id"])
    sub2 = next(s for s in body["subforums"] if s["epic_id"] == epic2["id"])
    assert len(sub1["topics"]) == 3
    assert len(sub2["topics"]) == 3

    chatty_topic = next(t for t in sub1["topics"] if t["task_id"] == chatty["id"])
    assert chatty_topic["comment_count"] == 2
    assert chatty_topic["last_comment_at"] is not None
    assert chatty_topic["last_comment_author_id"] is not None

    # All other tasks have zero comments and a null last-comment marker.
    for sub in body["subforums"]:
        for topic in sub["topics"]:
            if topic["task_id"] == chatty["id"]:
                continue
            assert topic["comment_count"] == 0
            assert topic["last_comment_at"] is None
            assert topic["last_comment_author_id"] is None

    # Auth/me + the aggregate itself should fit well under 10 statements.
    # The naive O(epics * 3) implementation would emit ~ (1 + 1 + 1 + 2*1 +
    # 6*2) = 17+ for this dataset; the new implementation is 4-5 flat.
    assert len(statements) <= 10, (
        f"forum aggregate emitted {len(statements)} SQL statements:\n"
        + "\n".join(statements)
    )
