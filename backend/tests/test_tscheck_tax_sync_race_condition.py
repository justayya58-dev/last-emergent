import asyncio
import uuid

import httpx

SUFFIX = uuid.uuid4().hex[:8]


def test_concurrent_tax_document_sync_does_not_500(client):
    """Regression for a TOCTOU race in routers/tax.py sync_sources(): the find_one-then-insert_one
    pattern is not atomic, so two near-simultaneous GET /auditpro/tax/documents calls that both
    need to sync the same new approved expense can both pass the "not yet synced" check and then
    race on the unique (source_type, source_id) index, crashing one request with an unhandled
    DuplicateKeyError -> 500 instead of idempotently returning the already-synced document.
    """
    payload = {
        "type": "expense",
        "transaction_date": "2026-05-01",
        "counterparty": f"tscheck-race-vendor-{SUFFIX}",
        "reference_number": f"TSK-RACE-{SUFFIX}",
        "category": "Operasional",
        "subtotal": 500000,
        "tax": 55000,
        "total": 555000,
    }
    created = client.post("/auditpro/transactions", json=payload)
    assert created.status_code == 200, created.text
    tid = created.json()["id"]
    assert client.post(f"/auditpro/transactions/{tid}/action", json={"action": "submit"}).status_code == 200
    assert client.post(f"/auditpro/transactions/{tid}/action", json={"action": "approve"}).status_code == 200

    # Each independent async client must carry the authenticated session cookie.
    session_cookie = client.cookies.get("auditpro_session")
    assert session_cookie, "client fixture must authenticate before the concurrency test"

    async def fetch_documents():
        async with httpx.AsyncClient(
            base_url=str(client.base_url),
            timeout=30.0,
            cookies={"auditpro_session": session_cookie},
        ) as async_client:
            return await async_client.get("/auditpro/tax/documents")

    async def fire_concurrent_requests():
        return await asyncio.gather(
            *[fetch_documents() for _ in range(6)],
            return_exceptions=True,
        )

    results = asyncio.run(fire_concurrent_requests())
    statuses = [r.status_code if not isinstance(r, Exception) else "exception" for r in results]
    assert all(status == 200 for status in statuses), f"Expected all 200s, got {statuses}"
