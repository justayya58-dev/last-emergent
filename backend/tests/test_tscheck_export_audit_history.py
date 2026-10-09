"""Criterion: Export activity recorded to audit trail (/exports/history) for each export type."""
import uuid

SUFFIX = uuid.uuid4().hex[:8]


def create_invoice(client):
    payload = {
        "customer": f"tscheck-audit-customer-{SUFFIX}",
        "due_date": "2030-01-01",
        "items": [{"description": "Jasa audit export tscheck", "unit": "jasa", "quantity": 1, "price": 500000, "total": 500000}],
        "tax_rate": 11,
    }
    response = client.post("/auditpro/invoices", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def latest_history_row(client):
    resp = client.get("/auditpro/exports/history")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert isinstance(rows, list)
    assert len(rows) <= 50
    return rows


def test_exports_history_returns_rows_newest_first(client):
    rows = latest_history_row(client)
    if len(rows) >= 2:
        assert rows[0]["created_at"] >= rows[1]["created_at"]


def test_business_export_pdf_writes_audit_log_row(client):
    before = latest_history_row(client)
    before_ids = {r["id"] for r in before}

    resp = client.get("/auditpro/reports/business-export.pdf")
    assert resp.status_code == 200, resp.text

    after = latest_history_row(client)
    new_rows = [r for r in after if r["id"] not in before_ids]
    assert new_rows, "expected a new export log row after business-export.pdf"
    row = new_rows[0]
    assert row["export_format"] == "pdf"
    assert row["export_type"] in ("business_report",)
    assert "created_at" in row


def test_invoice_pdf_export_writes_audit_log_row(client):
    invoice = create_invoice(client)
    before = latest_history_row(client)
    before_ids = {r["id"] for r in before}

    resp = client.get(f"/auditpro/invoices/{invoice['id']}/export.pdf")
    assert resp.status_code == 200, resp.text

    after = latest_history_row(client)
    new_rows = [r for r in after if r["id"] not in before_ids and r.get("export_type") == "invoice"]
    assert new_rows, "expected a new 'invoice' export log row after invoice export.pdf"
    row = new_rows[0]
    assert row["export_format"] == "pdf"


def test_tax_csv_export_writes_audit_log_row(client):
    before = latest_history_row(client)
    before_ids = {r["id"] for r in before}

    resp = client.get("/auditpro/tax/export.csv")
    assert resp.status_code == 200, resp.text

    after = latest_history_row(client)
    new_rows = [r for r in after if r["id"] not in before_ids]
    assert new_rows, "expected a new export log row after tax/export.csv"
    row = new_rows[0]
    assert row["export_format"] == "csv"
