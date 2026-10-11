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
