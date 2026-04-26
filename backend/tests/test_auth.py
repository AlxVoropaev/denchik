async def test_register_sets_cookie_and_returns_user(client):
    r = await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "hunter22", "display_name": "Bob"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "bob@example.com"
    assert body["display_name"] == "Bob"
    assert "denchik_session" in r.cookies


async def test_register_duplicate_email_conflict(client):
    payload = {"email": "dup@example.com", "password": "hunter22", "display_name": "Dup"}
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 409


async def test_login_wrong_password(client):
    await client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": "hunter22", "display_name": "X"},
    )
    r = await client.post(
        "/auth/login", json={"email": "x@example.com", "password": "WRONG"}
    )
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_returns_user_when_authenticated(auth_client):
    r = await auth_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


async def test_logout_clears_cookie(auth_client):
    r = await auth_client.post("/auth/logout")
    assert r.status_code == 200
    auth_client.cookies.clear()
    r2 = await auth_client.get("/auth/me")
    assert r2.status_code == 401
