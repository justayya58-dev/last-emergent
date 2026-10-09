"""Criterion: full status workflow draft -> finalize(pending) -> send(sent) -> mark_paid(paid),
and mark_overdue from sent/pending (not draft)."""
import uuid

SUFFIX = uuid.uuid4().hex[:8]


def create_draft(client, suffix):
    payload = {
        "customer": f"tscheck-workflow-{suffix}-{SUFFIX}",
        "due_date": "2030-01-01",
        "items": [{"description": "Jasa workflow tscheck", "unit": "jasa", "quantity": 1, "price": 800000, "total": 800000}],
        "tax_rate": 11,
        "finalize": False,
    }
    response = client.post("/auditpro/invoices", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_finalize_send_paid_full_workflow(client):
    invoice = create_draft(client, "fullflow")
    inv_id = invoice["id"]

    finalize = client.post(f"/auditpro/invoices/{inv_id}/action", json={"action": "finalize"})
    assert finalize.status_code == 200, finalize.text
    assert finalize.json()["status"] == "pending"

    send = client.post(f"/auditpro/invoices/{inv_id}/action", json={"action": "send"})
    assert send.status_code == 200, send.text
    assert send.json()["status"] == "sent"

    paid = client.post(f"/auditpro/invoices/{inv_id}/action", json={"action": "mark_paid"})
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["paid_at"]


def test_mark_overdue_from_sent_and_pending_but_not_draft(client):
    # from pending
    inv_pending = create_draft(client, "overdue-pending")
    finalize = client.post(f"/auditpro/invoices/{inv_pending['id']}/action", json={"action": "finalize"})
    assert finalize.status_code == 200, finalize.text
    overdue_pending = client.post(f"/auditpro/invoices/{inv_pending['id']}/action", json={"action": "mark_overdue"})
    assert overdue_pending.status_code == 200, overdue_pending.text
    assert overdue_pending.json()["status"] == "overdue"

    # from sent
    inv_sent = create_draft(client, "overdue-sent")
    client.post(f"/auditpro/invoices/{inv_sent['id']}/action", json={"action": "finalize"})
    client.post(f"/auditpro/invoices/{inv_sent['id']}/action", json={"action": "send"})
    overdue_sent = client.post(f"/auditpro/invoices/{inv_sent['id']}/action", json={"action": "mark_overdue"})
    assert overdue_sent.status_code == 200, overdue_sent.text
    assert overdue_sent.json()["status"] == "overdue"

    # from draft -> 409
    inv_draft = create_draft(client, "overdue-draft")
    overdue_draft = client.post(f"/auditpro/invoices/{inv_draft['id']}/action", json={"action": "mark_overdue"})
    assert overdue_draft.status_code == 409, overdue_draft.text
