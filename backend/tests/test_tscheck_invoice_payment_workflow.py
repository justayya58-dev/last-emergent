import uuid

SUFFIX = uuid.uuid4().hex[:8]


def create_invoice(client, due_date="2030-01-01"):
    payload = {
        "customer": f"tscheck-payment-customer-{SUFFIX}",
        "due_date": due_date,
        "items": [{"description": "Jasa tscheck", "unit": "jasa", "quantity": 1, "price": 1200000, "total": 1200000}],
        "tax_rate": 11,
    }
    response = client.post("/auditpro/invoices", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_draft_to_sent_to_paid_creates_income_transaction(client):
    invoice = create_invoice(client)
    invoice_id = invoice["id"]

    send = client.post(f"/auditpro/invoices/{invoice_id}/action", json={"action": "send"})
    assert send.status_code == 200, send.text
    assert send.json()["status"] == "sent"

    paid = client.post(f"/auditpro/invoices/{invoice_id}/action", json={"action": "mark_paid"})
    assert paid.status_code == 200, paid.text
    paid_body = paid.json()
    assert paid_body["status"] == "paid"
    assert paid_body["paid_at"]

    transactions = client.get("/auditpro/transactions")
    assert transactions.status_code == 200, transactions.text
    matches = [t for t in transactions.json() if t["source"] == "invoice" and t["reference_number"] == invoice["number"]]
    assert len(matches) == 1
    income_tx = matches[0]
    assert income_tx["type"] == "income"
    assert income_tx["status"] == "approved"
    assert income_tx["total"] == invoice["total"]


def test_invalid_invoice_transition_is_rejected(client):
    invoice = create_invoice(client, due_date="2030-02-01")
    # cannot mark_paid directly from draft
    response = client.post(f"/auditpro/invoices/{invoice['id']}/action", json={"action": "mark_paid"})
    assert response.status_code == 409


def test_concurrent_mark_paid_records_only_one_income_transaction(client):
    import os
    from concurrent.futures import ThreadPoolExecutor

    username = os.environ.get("AUDITPRO_ADMIN_USERNAME", "auditpro-admin")
    password = os.environ.get("AUDITPRO_ADMIN_PASSWORD", "")
    if not password:
        import pytest
        pytest.skip("Set AUDITPRO_ADMIN_PASSWORD to run authenticated concurrency tests")

    invoice = create_invoice(client, due_date="2030-03-01")
    invoice_id = invoice["id"]
    sent = client.post(f"/auditpro/invoices/{invoice_id}/action", json={"action": "send"})
    assert sent.status_code == 200, sent.text

    def mark_paid():
        with httpx.Client(base_url=str(client.base_url), timeout=30.0) as concurrent_client:
            login = concurrent_client.post("auth/login", json={"username": username, "password": password})
            assert login.status_code == 200, login.text
            return concurrent_client.post(
                f"auditpro/invoices/{invoice_id}/action",
                json={"action": "mark_paid"},
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: mark_paid(), range(2)))

    assert sum(response.status_code == 200 for response in responses) == 1
    assert all(response.status_code in (200, 409) for response in responses)
    transactions = client.get("/auditpro/transactions")
    assert transactions.status_code == 200, transactions.text
    matches = [
        item for item in transactions.json()
        if item["source"] == "invoice" and item["reference_number"] == invoice["number"]
    ]
    assert len(matches) == 1
