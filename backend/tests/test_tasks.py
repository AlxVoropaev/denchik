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


async def test_create_task_drops_foreign_workspace_label(auth_client, workspace, epic, client):
    """A label whose workspace differs from the task's must not attach (cross-ws leak)."""
    # Alice's own label in her workspace (must remain attachable).
    own_label = await auth_client.post(
        "/labels",
        json={"workspace_id": workspace["id"], "name": "own", "color": "#00ff00"},
    )
    assert own_label.status_code == 201
    own_lid = own_label.json()["id"]

    # Save Alice's cookie and switch to a fresh user Eve who creates her own workspace + label.
    alice_cookie = client.cookies.get("denchik_session")
    client.cookies.clear()
    reg = await client.post(
        "/auth/register",
        json={"email": "eve@example.com", "password": "hunter22", "display_name": "Eve"},
    )
    assert reg.status_code == 201
    eve_ws = await client.post("/workspaces", json={"name": "Eve-WS"})
    assert eve_ws.status_code == 201
    eve_ws_id = eve_ws.json()["id"]
    eve_label = await client.post(
        "/labels",
        json={"workspace_id": eve_ws_id, "name": "secret", "color": "#0000ff"},
    )
    assert eve_label.status_code == 201
    foreign_lid = eve_label.json()["id"]

    # Restore Alice's session.
    client.cookies.clear()
    client.cookies.set("denchik_session", alice_cookie)

    # Create path: foreign id alone — must result in zero labels attached.
    r = await client.post(
        "/tasks",
        json={"epic_id": epic["id"], "title": "Sneaky", "label_ids": [foreign_lid]},
    )
    assert r.status_code == 201, r.text
    assert r.json()["labels"] == []

    # Create path: mix of own + foreign — only the own label survives.
    r2 = await client.post(
        "/tasks",
        json={
            "epic_id": epic["id"],
            "title": "Mixed",
            "label_ids": [own_lid, foreign_lid],
        },
    )
    assert r2.status_code == 201, r2.text
    assert [l["id"] for l in r2.json()["labels"]] == [own_lid]


async def test_patch_task_drops_foreign_workspace_label(auth_client, workspace, epic, client):
    """PATCH /tasks/{id} with a foreign label_id must not attach it."""
    # Create a task in Alice's workspace.
    t = (
        await auth_client.post("/tasks", json={"epic_id": epic["id"], "title": "T"})
    ).json()

    # Switch to Eve, create her workspace + label, capture foreign id.
    alice_cookie = client.cookies.get("denchik_session")
    client.cookies.clear()
    reg = await client.post(
        "/auth/register",
        json={"email": "mallory@example.com", "password": "hunter22", "display_name": "M"},
    )
    assert reg.status_code == 201
    other_ws = await client.post("/workspaces", json={"name": "Other"})
    assert other_ws.status_code == 201
    other_label = await client.post(
        "/labels",
        json={"workspace_id": other_ws.json()["id"], "name": "x", "color": "#abcdef"},
    )
    assert other_label.status_code == 201
    foreign_lid = other_label.json()["id"]

    # Restore Alice and try to PATCH the foreign id onto her task.
    client.cookies.clear()
    client.cookies.set("denchik_session", alice_cookie)
    r = await client.patch(f"/tasks/{t['id']}", json={"label_ids": [foreign_lid]})
    assert r.status_code == 200, r.text
    # Re-fetch via a separate request to guarantee a fresh DB read (the session
    # behind PATCH may serve a stale collection from the identity map).
    g = await client.get(f"/tasks/{t['id']}")
    assert g.status_code == 200
    assert g.json()["labels"] == []
