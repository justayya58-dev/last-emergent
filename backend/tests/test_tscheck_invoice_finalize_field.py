"""Criterion: POST /api/auditpro/invoices `finalize` field -> draft vs pending status."""
import uuid

SUFFIX = uuid.uuid4().hex[:8]


def make_payload(customer_suffix, finalize=None):
    payload = {
        "customer": f"tscheck-finalize-{customer_suffix}-{SUFFIX}",
        "due_date": "2030-05-01",
        "items": [{"description": "Jasa tscheck finalize", "unit": "jasa", "quantity": 1, "price": 1000000, "total": 1000000}],
        "tax_rate": 11,
    }
    if finalize is not None:
        payload["finalize"] = finalize
    return payload


def test_finalize_false_or_absent_creates_draft(client):
    response = client.post("/auditpro/invoices", json=make_payload("draft", finalize=False))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["number"]

    listed = client.get("/auditpro/invoices")
    assert any(row["id"] == body["id"] and row["status"] == "draft" for row in listed.json())


def test_finalize_true_creates_pending(client):
    response = client.post("/auditpro/invoices", json=make_payload("pending", finalize=True))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["number"]

    listed = client.get("/auditpro/invoices")
    assert any(row["id"] == body["id"] and row["status"] == "pending" for row in listed.json())
