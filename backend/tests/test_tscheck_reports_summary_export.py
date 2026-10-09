"""Criterion: Reports summary shows approved sales/expenses/net profit/receivables/tax; CSV export returns 200."""


def test_reports_summary_returns_expected_fields(client):
    resp = client.get("/auditpro/reports/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for field in ("sales_total", "expense_total", "net_profit", "receivables", "tax_collected", "tax_paid"):
        assert field in body, f"missing field {field} in {body}"
    assert body["net_profit"] == body["sales_total"] - body["expense_total"]


def test_reports_export_csv_returns_200_with_csv_content(client):
    resp = client.get("/auditpro/reports/export.csv")
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")
    body = resp.text
    assert len(body.strip().splitlines()) >= 1
