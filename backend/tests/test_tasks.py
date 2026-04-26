async def test_quick_create_task_with_only_title_and_epic(auth_client, epic):
    """Central UX: a task should be created with just epic_id + title."""
    r = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "Add login"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Add login"
    assert body["status"] == "todo"
    assert body["priority"] == "med"
    assert body["assignee_id"] is None
    assert body["due_date"] is None
    assert body["position"] == 0
    assert body["labels"] == []


async def test_task_positions_increment(auth_client, epic):
    r1 = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "A"})
    r2 = await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "B"})
    assert r1.json()["position"] == 0
    assert r2.json()["position"] == 1


async def test_patch_task_status_and_title(auth_client, epic):
    t = (await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "X"})).json()
    r = await auth_client.patch(
        f"/tasks/{t['id']}", json={"status": "in_progress", "title": "X-renamed"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["title"] == "X-renamed"


async def test_delete_task(auth_client, epic):
    t = (await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "X"})).json()
    r = await auth_client.delete(f"/tasks/{t['id']}")
    assert r.status_code == 204
    g = await auth_client.get(f"/tasks/{t['id']}")
    assert g.status_code == 404


async def test_unauthenticated_cannot_create_task(client, epic):
    client.cookies.clear()
    r = await client.post("/tasks", json={"epic_id": epic["id"], "title": "Nope"})
    assert r.status_code == 401


async def test_task_with_labels(auth_client, workspace, epic):
    label = await auth_client.post(
        "/labels", json={"workspace_id": workspace["id"], "name": "bug", "color": "#ff0000"}
    )
    assert label.status_code == 201
    lid = label.json()["id"]
    r = await auth_client.post(
        "/tasks", json={"epic_id": epic["id"], "title": "Buggy", "label_ids": [lid]}
    )
    assert r.status_code == 201
    assert [l["id"] for l in r.json()["labels"]] == [lid]
