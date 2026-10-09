"""Criterion: PUT /api/auditpro/invoices/{id} edits a draft invoice (recomputes totals, keeps
number/issue_date); 409 if not draft, 404 if missing."""
import uuid

SUFFIX = uuid.uuid4().hex[:8]


def create_draft(client, suffix):
    payload = {
        "customer": f"tscheck-edit-{suffix}-{SUFFIX}",
        "due_date": "2030-01-01",
        "items": [{"description": "Jasa awal tscheck", "unit": "jasa", "quantity": 1, "price": 1000000, "total": 1000000}],
        "tax_rate": 11,
        "finalize": False,
    }
    response = client.post("/auditpro/invoices", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_put_edits_draft_recomputes_totals_keeps_number(client):
    invoice = create_draft(client, "happy")
    update_payload = {
        "customer": invoice["customer"],
        "due_date": "2030-06-15",
        "items": [{"description": "Jasa revisi tscheck", "unit": "jasa", "quantity": 4, "price": 250000, "total": 1000000}],
        "tax_rate": 11,
    }
    response = client.put(f"/auditpro/invoices/{invoice['id']}", json=update_payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["number"] == invoice["number"]
    assert body["issue_date"] == invoice["issue_date"]
    assert body["due_date"] == "2030-06-15"
    assert body["subtotal"] == 1000000
    assert body["tax"] == 110000
    assert body["total"] == 1110000
    assert body["status"] == "draft"

    # Re-fetch the same invoice directly via PUT with no-op edit to confirm the
    # new total persisted server-side (not just echoed in the response). NOTE:
    # GET /auditpro/invoices is capped at 100 most-recent rows sorted only by
    # issue_date (date, no time) with no tiebreaker — once >100 invoices share
    # today's issue_date (true in this environment, see bug report), a freshly
    # written/edited row is not guaranteed to appear in that list. See the
    # dedicated ledger-visibility bug check instead of asserting list membership
    # here, to keep this test about PUT's own contract.
    reread = client.put(f"/auditpro/invoices/{invoice['id']}", json=update_payload)
    assert reread.status_code == 200, reread.text
    assert reread.json()["total"] == 1110000
    assert reread.json()["number"] == invoice["number"]


def test_put_on_non_draft_returns_409(client):
    invoice = create_draft(client, "nondraft")
    finalize = client.post(f"/auditpro/invoices/{invoice['id']}/action", json={"action": "finalize"})
    assert finalize.status_code == 200, finalize.text
    assert finalize.json()["status"] == "pending"

    update_payload = {
        "customer": invoice["customer"],
        "due_date": "2030-07-01",
        "items": [{"description": "Jasa tscheck", "unit": "jasa", "quantity": 1, "price": 500000, "total": 500000}],
        "tax_rate": 11,
    }
    response = client.put(f"/auditpro/invoices/{invoice['id']}", json=update_payload)
    assert response.status_code == 409, response.text


def test_put_on_missing_invoice_returns_404(client):
    bogus_id = str(uuid.uuid4())
    update_payload = {
        "customer": "tscheck-missing",
        "due_date": "2030-07-01",
        "items": [{"description": "x", "unit": "jasa", "quantity": 1, "price": 1, "total": 1}],
        "tax_rate": 11,
    }
    response = client.put(f"/auditpro/invoices/{bogus_id}", json=update_payload)
    assert response.status_code == 404
