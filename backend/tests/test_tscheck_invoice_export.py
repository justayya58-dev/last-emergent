"""Criterion: Invoice PDF/Excel export returns a downloadable file; nonexistent id -> 404."""
import uuid

SUFFIX = uuid.uuid4().hex[:8]


def create_invoice(client):
    payload = {
        "customer": f"tscheck-export-customer-{SUFFIX}",
        "due_date": "2030-01-01",
        "items": [{"description": "Jasa export tscheck", "unit": "jasa", "quantity": 1, "price": 900000, "total": 900000}],
        "tax_rate": 11,
    }
    response = client.post("/auditpro/invoices", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_pdf_export_returns_downloadable_file(client):
    invoice = create_invoice(client)
    resp = client.get(f"/auditpro/invoices/{invoice['id']}/export.pdf")
    assert resp.status_code == 200, resp.text
    assert "pdf" in resp.headers.get("content-type", "").lower()
    assert len(resp.content) > 0
    assert resp.content[:4] == b"%PDF"


def test_xlsx_export_returns_downloadable_file(client):
    invoice = create_invoice(client)
    resp = client.get(f"/auditpro/invoices/{invoice['id']}/export.xlsx")
    assert resp.status_code == 200, resp.text
    assert "spreadsheetml" in resp.headers.get("content-type", "").lower()
    assert resp.content[:2] == b"PK", "xlsx is a zip container and must start with PK signature"


def test_export_nonexistent_invoice_returns_404(client):
    bogus_id = str(uuid.uuid4())
    pdf_resp = client.get(f"/auditpro/invoices/{bogus_id}/export.pdf")
    assert pdf_resp.status_code == 404
    xlsx_resp = client.get(f"/auditpro/invoices/{bogus_id}/export.xlsx")
    assert xlsx_resp.status_code == 404
