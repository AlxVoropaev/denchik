async def test_create_workspace_makes_owner_member(auth_client):
    r = await auth_client.post("/workspaces", json={"name": "Acme"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Acme"

    # The owner should see the workspace listed
    lr = await auth_client.get("/workspaces")
    assert lr.status_code == 200
    assert any(w["id"] == body["id"] for w in lr.json())


async def test_non_member_cannot_access_workspace_resources(auth_client, client, workspace):
    # Register a second user
    r = await client.post(
        "/auth/register",
        json={"email": "eve@example.com", "password": "hunter22", "display_name": "Eve"},
    )
    assert r.status_code == 201
    # Eve tries to create an epic group in Alice's workspace
    r2 = await client.post(
        "/epic-groups", json={"workspace_id": workspace["id"], "name": "Sneaky"}
    )
    assert r2.status_code == 403
