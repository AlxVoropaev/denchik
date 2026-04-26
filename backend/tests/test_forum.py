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
