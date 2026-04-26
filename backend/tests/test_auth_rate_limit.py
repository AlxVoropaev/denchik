"""Rate-limit coverage for /auth/login and /auth/register.

Both endpoints are protected by slowapi (login: 5/minute, register: 10/hour
per IP). The ``app`` fixture resets the limiter before each test, so
counters start from zero here.
"""


async def test_login_rate_limit_allows_then_blocks(client):
    # 5 wrong-password attempts: each should still hit the handler and 401.
    for _ in range(5):
        r = await client.post(
            "/auth/login", json={"email": "ghost@example.com", "password": "nope"}
        )
        assert r.status_code == 401, r.text

    # The 6th attempt is short-circuited by slowapi → 429 with a non-empty body.
    r = await client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "nope"}
    )
    assert r.status_code == 429
    assert r.text  # standard slowapi handler emits a body describing the limit.


async def test_register_rate_limit_blocks_after_ten(client):
    # 10 registrations succeed (each with a unique email).
    for i in range(10):
        r = await client.post(
            "/auth/register",
            json={
                "email": f"user{i}@example.com",
                "password": "hunter22",
                "display_name": f"User {i}",
            },
        )
        assert r.status_code == 201, r.text
        # Drop the cookie so the next register call still looks like a fresh client.
        client.cookies.clear()

    # 11th hit is throttled before the handler runs.
    r = await client.post(
        "/auth/register",
        json={
            "email": "overflow@example.com",
            "password": "hunter22",
            "display_name": "Overflow",
        },
    )
    assert r.status_code == 429
    assert r.text
