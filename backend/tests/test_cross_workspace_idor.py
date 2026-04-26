"""Cross-workspace IDOR negative tests.

For every endpoint that takes a workspace-scoped resource id, we assert that a
user authenticated as a member of *another* workspace cannot reach that
resource. The expected status is whatever ``require_workspace_member`` returns
(403) or whatever the existing-row check returns first (404 for a missing
row). We accept both — both are valid IDOR-defeating responses.

Test isolation note (from CLAUDE.md): ``client`` and ``auth_client`` share a
cookie jar. We register user_A, populate workspace_A, then ``cookies.clear()``
and register user_B before probing user_A's ids.

If a test xfails here, the leak is real. The TODO/comment names the next PR
that should land the fix — *this* PR is the test net only.
"""
import io

import pytest_asyncio


# ---------------------------------------------------------------------------
# Shared two-workspace fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def two_workspaces(client):
    """Build user_A + workspace_A (with full row hierarchy) and user_B +
    workspace_B (empty). Returns a dict + the *client* logged in as user_B.

    User_A's resources are populated first, then we clear cookies, register
    user_B, and create workspace_B. The returned ``client`` carries user_B's
    session cookie, so any direct call on it acts as user_B.
    """
    # --- user_A ---
    r = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "secretpw",
            "display_name": "Alice",
        },
    )
    assert r.status_code == 201, r.text

    ws_a = (await client.post("/workspaces", json={"name": "Acme-A"})).json()
    group_a = (
        await client.post(
            "/epic-groups", json={"workspace_id": ws_a["id"], "name": "Backlog-A"}
        )
    ).json()
    epic_a = (
        await client.post(
            "/epics", json={"epic_group_id": group_a["id"], "name": "Auth-A"}
        )
    ).json()
    task_a = (
        await client.post(
            "/tasks", json={"epic_id": epic_a["id"], "title": "Task-A"}
        )
    ).json()
    label_a = (
        await client.post(
            "/labels",
            json={"workspace_id": ws_a["id"], "name": "bug", "color": "#ff0000"},
        )
    ).json()
    comment_a = (
        await client.post(
            f"/tasks/{task_a['id']}/comments", json={"body": "Alice's comment"}
        )
    ).json()
    upload_a = await client.post(
        f"/tasks/{task_a['id']}/attachments",
        files={"file": ("a.txt", io.BytesIO(b"alice"), "text/plain")},
    )
    assert upload_a.status_code == 201, upload_a.text
    attachment_a = upload_a.json()

    # --- swap to user_B ---
    client.cookies.clear()
    r = await client.post(
        "/auth/register",
        json={
            "email": "bob@example.com",
            "password": "secretpw",
            "display_name": "Bob",
        },
    )
    assert r.status_code == 201, r.text

    ws_b = (await client.post("/workspaces", json={"name": "Acme-B"})).json()
    group_b = (
        await client.post(
            "/epic-groups", json={"workspace_id": ws_b["id"], "name": "Backlog-B"}
        )
    ).json()
    epic_b = (
        await client.post(
            "/epics", json={"epic_group_id": group_b["id"], "name": "Auth-B"}
        )
    ).json()

    return {
        "client": client,  # logged in as Bob
        "ws_a": ws_a,
        "group_a": group_a,
        "epic_a": epic_a,
        "task_a": task_a,
        "label_a": label_a,
        "comment_a": comment_a,
        "attachment_a": attachment_a,
        "ws_b": ws_b,
        "epic_b": epic_b,
    }


def _idor(resp):
    """A correct IDOR response is 403 (not a member) or 404 (hidden)."""
    return resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Epics
# ---------------------------------------------------------------------------
# NOTE: There is no ``GET /epics/{id}`` endpoint — only ``GET /epics`` (list,
# query-param scoped). The user's spec listed a singular GET; documenting the
# absence here so future reviewers don't think it was forgotten.


async def test_idor_patch_epic(two_workspaces):
    bob = two_workspaces["client"]
    eid = two_workspaces["epic_a"]["id"]
    r = await bob.patch(f"/epics/{eid}", json={"name": "pwned"})
    assert _idor(r), r.status_code


async def test_idor_delete_epic(two_workspaces):
    bob = two_workspaces["client"]
    eid = two_workspaces["epic_a"]["id"]
    r = await bob.delete(f"/epics/{eid}")
    assert _idor(r), r.status_code


async def test_idor_list_epics_in_other_ws(two_workspaces):
    """``GET /epics?epic_group_id=<A>`` from a non-member must not list rows."""
    bob = two_workspaces["client"]
    gid = two_workspaces["group_a"]["id"]
    r = await bob.get(f"/epics?epic_group_id={gid}")
    assert _idor(r), r.status_code


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


async def test_idor_get_task(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.get(f"/tasks/{tid}")
    assert _idor(r), r.status_code


async def test_idor_patch_task(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.patch(f"/tasks/{tid}", json={"title": "pwned"})
    assert _idor(r), r.status_code


async def test_idor_delete_task(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.delete(f"/tasks/{tid}")
    assert _idor(r), r.status_code


async def test_idor_list_tasks_in_other_ws_epic(two_workspaces):
    bob = two_workspaces["client"]
    eid = two_workspaces["epic_a"]["id"]
    r = await bob.get(f"/tasks?epic_id={eid}")
    assert _idor(r), r.status_code


async def test_idor_create_task_in_other_ws_epic(two_workspaces):
    bob = two_workspaces["client"]
    eid = two_workspaces["epic_a"]["id"]
    r = await bob.post("/tasks", json={"epic_id": eid, "title": "sneak"})
    # Creation must be refused — 403 from RBAC check.
    assert _idor(r), r.status_code


async def test_idor_move_own_task_into_other_ws_epic(two_workspaces):
    """PATCH /tasks/{own_id} with epic_id pointing at workspace_A must fail.

    This is the "smuggle a task into another workspace via PATCH" path.
    """
    bob = two_workspaces["client"]
    own_task = (
        await bob.post(
            "/tasks", json={"epic_id": two_workspaces["epic_b"]["id"], "title": "own"}
        )
    ).json()
    target_epic = two_workspaces["epic_a"]["id"]
    r = await bob.patch(f"/tasks/{own_task['id']}", json={"epic_id": target_epic})
    assert _idor(r), r.status_code


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
# Comments live under /tasks/{task_id}/comments — there's no /comments?task_id=
# endpoint, so the spec's wording is interpreted as that nested path.


async def test_idor_list_comments(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.get(f"/tasks/{tid}/comments")
    assert _idor(r), r.status_code


async def test_idor_create_comment(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.post(f"/tasks/{tid}/comments", json={"body": "hi from Bob"})
    assert _idor(r), r.status_code


async def test_idor_patch_comment(two_workspaces):
    """Bob edits Alice's comment on a task in workspace_A."""
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    cid = two_workspaces["comment_a"]["id"]
    r = await bob.patch(
        f"/tasks/{tid}/comments/{cid}", json={"body": "rewritten"}
    )
    assert _idor(r), r.status_code


async def test_idor_delete_comment(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    cid = two_workspaces["comment_a"]["id"]
    r = await bob.delete(f"/tasks/{tid}/comments/{cid}")
    assert _idor(r), r.status_code


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


async def test_idor_list_attachments(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.get(f"/tasks/{tid}/attachments")
    assert _idor(r), r.status_code


async def test_idor_upload_attachment(two_workspaces):
    bob = two_workspaces["client"]
    tid = two_workspaces["task_a"]["id"]
    r = await bob.post(
        f"/tasks/{tid}/attachments",
        files={"file": ("hack.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert _idor(r), r.status_code


async def test_idor_download_attachment(two_workspaces):
    bob = two_workspaces["client"]
    aid = two_workspaces["attachment_a"]["id"]
    r = await bob.get(f"/attachments/{aid}/download")
    assert _idor(r), r.status_code


# ---------------------------------------------------------------------------
# Forum
# ---------------------------------------------------------------------------


async def test_idor_forum_view(two_workspaces):
    bob = two_workspaces["client"]
    gid = two_workspaces["group_a"]["id"]
    r = await bob.get(f"/forum/{gid}")
    assert _idor(r), r.status_code


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


async def test_idor_list_labels(two_workspaces):
    bob = two_workspaces["client"]
    wid = two_workspaces["ws_a"]["id"]
    r = await bob.get(f"/labels?workspace_id={wid}")
    assert _idor(r), r.status_code


async def test_idor_create_label_in_other_ws(two_workspaces):
    bob = two_workspaces["client"]
    wid = two_workspaces["ws_a"]["id"]
    r = await bob.post(
        "/labels",
        json={"workspace_id": wid, "name": "snek", "color": "#000000"},
    )
    assert _idor(r), r.status_code


# ---------------------------------------------------------------------------
# Epic groups (additional surface — adjacent to the spec's GET /workspaces/{id})
# ---------------------------------------------------------------------------
# NOTE: There is no ``GET /workspaces/{id}`` endpoint. The list endpoint
# ``GET /workspaces`` already filters by membership in a join, so a non-member
# simply won't see the row. We instead probe the next-best workspace-scoped
# read: ``GET /epic-groups?workspace_id=<A>`` and ``DELETE /epic-groups/{id}``.


async def test_idor_list_epic_groups_in_other_ws(two_workspaces):
    bob = two_workspaces["client"]
    wid = two_workspaces["ws_a"]["id"]
    r = await bob.get(f"/epic-groups?workspace_id={wid}")
    assert _idor(r), r.status_code


async def test_idor_delete_epic_group(two_workspaces):
    bob = two_workspaces["client"]
    gid = two_workspaces["group_a"]["id"]
    r = await bob.delete(f"/epic-groups/{gid}")
    assert _idor(r), r.status_code


async def test_idor_create_epic_group_in_other_ws(two_workspaces):
    bob = two_workspaces["client"]
    wid = two_workspaces["ws_a"]["id"]
    r = await bob.post(
        "/epic-groups", json={"workspace_id": wid, "name": "sneak"}
    )
    assert _idor(r), r.status_code


async def test_idor_create_epic_in_other_ws_group(two_workspaces):
    bob = two_workspaces["client"]
    gid = two_workspaces["group_a"]["id"]
    r = await bob.post(
        "/epics", json={"epic_group_id": gid, "name": "sneak"}
    )
    assert _idor(r), r.status_code


async def test_idor_workspace_listing_excludes_other_ws(two_workspaces):
    """The closest analogue to ``GET /workspaces/{id}``: the list must not
    include workspace_A in Bob's response."""
    bob = two_workspaces["client"]
    r = await bob.get("/workspaces")
    assert r.status_code == 200
    ws_a_id = two_workspaces["ws_a"]["id"]
    assert all(w["id"] != ws_a_id for w in r.json()), r.json()
