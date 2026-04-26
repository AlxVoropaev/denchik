import logging


async def test_register_password_redacted_from_request_log(client, caplog):
    payload = {
        "email": "redact@example.com",
        "password": "super-secret-pw-123",
        "display_name": "Redact",
    }
    with caplog.at_level(logging.INFO, logger="denchik"):
        r = await client.post("/auth/register", json=payload)
    assert r.status_code == 201, r.text

    request_log_lines = [
        rec.getMessage()
        for rec in caplog.records
        if rec.name == "denchik" and "/auth/register" in rec.getMessage() and "→" in rec.getMessage()
    ]
    assert request_log_lines, "expected request log line for /auth/register"
    joined = "\n".join(request_log_lines)
    assert payload["password"] not in joined, (
        f"plaintext password leaked into denchik log: {joined!r}"
    )
    assert "<redacted>" in joined, (
        f"expected '<redacted>' marker in denchik log, got: {joined!r}"
    )
