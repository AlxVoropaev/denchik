async def test_create_epic_group_and_epic(auth_client, workspace):
    g = await auth_client.post(
        "/epic-groups", json={"workspace_id": workspace["id"], "name": "Backlog"}
    )
    assert g.status_code == 201
    gid = g.json()["id"]

    e = await auth_client.post("/epics", json={"epic_group_id": gid, "name": "Auth"})
    assert e.status_code == 201
    assert e.json()["name"] == "Auth"

    list_resp = await auth_client.get("/epics", params={"epic_group_id": gid})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


async def test_positions_increment(auth_client, epic_group):
    e1 = await auth_client.post(
        "/epics", json={"epic_group_id": epic_group["id"], "name": "A"}
    )
    e2 = await auth_client.post(
        "/epics", json={"epic_group_id": epic_group["id"], "name": "B"}
    )
    assert e1.json()["position"] == 0
    assert e2.json()["position"] == 1
