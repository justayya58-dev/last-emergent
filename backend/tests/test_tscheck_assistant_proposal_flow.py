import json

import httpx


def parse_sse_events(raw_text: str):
    events = []
    current_event = None
    for line in raw_text.splitlines():
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and current_event:
            data_raw = line.split(":", 1)[1].strip()
            try:
                events.append((current_event, json.loads(data_raw)))
            except json.JSONDecodeError:
                events.append((current_event, data_raw))
            current_event = None
    return events


def test_session_create_quick_prompts_and_grounded_streaming_response(client):
    prompts = client.get("/auditpro/assistant/quick-prompts")
    assert prompts.status_code == 200, prompts.text
    assert len(prompts.json()) > 0

    session = client.post("/auditpro/assistant/sessions", json={})
    assert session.status_code == 200, session.text
    session_id = session.json()["id"]

    with httpx.Client(base_url=client.base_url, timeout=40.0) as streaming_client:
        streaming_client.cookies.update(client.cookies)
        with streaming_client.stream(
            "POST",
            f"/auditpro/assistant/sessions/{session_id}/messages",
            json={"message": "Berapa total piutang saat ini dan invoice mana yang perlu ditagih?"},
        ) as response:
            assert response.status_code == 200
            raw_text = "".join(response.iter_text())

    events = parse_sse_events(raw_text)
    event_types = [event_type for event_type, _ in events]
    assert "meta" in event_types
    assert "delta" in event_types
    assert "done" in event_types

    full_answer = "".join(data["content"] for event_type, data in events if event_type == "delta")
    assert "Rp" in full_answer or "piutang" in full_answer.lower()

    history = client.get(f"/auditpro/assistant/sessions/{session_id}")
    assert history.status_code == 200, history.text
    messages = history.json()["messages"]
    assert any(m["role"] == "user" for m in messages)
    assert any(m["role"] == "assistant" for m in messages)


def test_proposal_requires_explicit_confirmation_before_creating_draft(client):
    session = client.post("/auditpro/assistant/sessions", json={}).json()
    session_id = session["id"]

    proposal_id = None
    with httpx.Client(base_url=client.base_url, timeout=40.0) as streaming_client:
        streaming_client.cookies.update(client.cookies)
        with streaming_client.stream(
            "POST",
            f"/auditpro/assistant/sessions/{session_id}/messages",
            json={"message": "Tolong buatkan draft laporan ringkas penjualan bulan ini untuk saya konfirmasi nanti."},
        ) as response:
            assert response.status_code == 200
            raw_text = "".join(response.iter_text())
    events = parse_sse_events(raw_text)
    for event_type, data in events:
        if event_type == "proposal":
            proposal_id = data["id"]
            assert data["status"] == "pending"
            break
    assert proposal_id, f"Expected a proposal event, got event types: {[e for e, _ in events]}"

    # Audit trail should record proposal creation, but no draft report exists yet pre-confirmation.
    audit_before = client.get(f"/auditpro/assistant/sessions/{session_id}/audit")
    assert audit_before.status_code == 200, audit_before.text
    assert any(event["action"] == "proposal_created" for event in audit_before.json())

    decision = client.post(f"/auditpro/assistant/proposals/{proposal_id}/decision", json={"confirm": True})
    assert decision.status_code == 200, decision.text
    confirmed = decision.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["result_id"]

    audit_after = client.get(f"/auditpro/assistant/sessions/{session_id}/audit")
    assert audit_after.status_code == 200, audit_after.text
    assert any(event["action"] == "proposal_confirmed" or "confirm" in event["action"] for event in audit_after.json())


def test_cancelling_a_proposal_does_not_create_a_draft(client):
    session = client.post("/auditpro/assistant/sessions", json={}).json()
    session_id = session["id"]
    proposal_id = None
    with httpx.Client(base_url=client.base_url, timeout=40.0) as streaming_client:
        streaming_client.cookies.update(client.cookies)
        with streaming_client.stream(
            "POST",
            f"/auditpro/assistant/sessions/{session_id}/messages",
            json={"message": "Buatkan draft laporan piutang untuk saya review, tapi saya belum tentu jadi pakai."},
        ) as response:
            assert response.status_code == 200
            raw_text = "".join(response.iter_text())
    events = parse_sse_events(raw_text)
    for event_type, data in events:
        if event_type == "proposal":
            proposal_id = data["id"]
            break
    assert proposal_id, f"Expected a proposal event, got event types: {[e for e, _ in events]}"

    decision = client.post(f"/auditpro/assistant/proposals/{proposal_id}/decision", json={"confirm": False})
    assert decision.status_code == 200, decision.text
    body = decision.json()
    assert body["status"] == "cancelled"
    assert body["result_id"] is None
