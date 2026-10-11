"""Regression tests for the workspace authentication boundary."""
def test_sensitive_endpoints_reject_anonymous_requests(client):
    # The client fixture logs in when AUDITPRO_ADMIN_PASSWORD is configured.
    client.cookies.clear()
    for method, path, kwargs in [
        ("get", "/auditpro/dashboard", {}),
        ("get", "/auditpro/transactions", {}),
        ("post", "/auditpro/transactions", {"json": {
            "type": "expense", "counterparty": "tscheck-noauth", "reference_number": "TSK-NOAUTH-1",
            "category": "Operasional", "subtotal": 1000, "tax": 0, "total": 1000,
        }}),
        ("get", "/auditpro/tax/summary", {}),
    ]:
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 401, f"{method.upper()} {path}: expected 401, got {response.status_code}"


def test_login_rejects_invalid_credentials(client):
    client.cookies.clear()
    response = client.post("/auth/login", json={"username": "not-admin", "password": "incorrect"})
    assert response.status_code in (401, 503), response.text


def test_configured_admin_login_issues_http_only_session_cookie(client):
    import os

    username = os.environ.get("AUDITPRO_ADMIN_USERNAME", "auditpro-admin")
    password = os.environ.get("AUDITPRO_ADMIN_PASSWORD", "")
    if not password:
        import pytest
        pytest.skip("Set AUDITPRO_ADMIN_PASSWORD in the test environment")
    client.cookies.clear()
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    cookie = response.headers.get("set-cookie", "").lower()
    assert "auditpro_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "max-age=28800" in cookie
    assert client.get("/auth/me").status_code == 200
    assert client.get("/auditpro/dashboard").status_code == 200
