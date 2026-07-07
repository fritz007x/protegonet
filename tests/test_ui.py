from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from cyber_agent.api.main import app
from cyber_agent.data.store import init_db, upsert_vendor

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Redirect the audit/vendor DB at a tmp file so UI tests stay hermetic."""
    from cyber_agent import config as cfg

    object.__setattr__(cfg.settings, "audit_db_path", str(tmp_path / "audit.sqlite"))
    init_db()
    yield


def test_index_serves_gui():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Protego" in res.text


def test_analyze_accepts_pasted_text():
    res = client.post("/analyze", data={"text": "Vendor: Acme\nInvoice Number: INV-1\nTotal: $100.00"})
    assert res.status_code == 200
    body = res.json()
    assert body["trace_id"]
    assert "decision" in body["state"]


def test_analyze_accepts_file_upload():
    res = client.post(
        "/analyze",
        files={"file": ("invoice.txt", b"Vendor: Acme\nTotal: $250.00", "text/plain")},
    )
    assert res.status_code == 200
    assert res.json()["trace_id"]


def test_resume_rejects_missing_token():
    """The HMAC approval token is mandatory — a tokenless resume must be refused."""
    res = client.post("/resume/some-thread", data={"approved": "true", "notes": ""})
    assert res.status_code == 403


def test_resume_rejects_invalid_token():
    res = client.post(
        "/resume/some-thread",
        data={"approved": "true", "notes": "", "token_exp": "9999999999", "token_sig": "deadbeef"},
    )
    assert res.status_code == 403


BANK_CHANGE_INVOICE = (
    "Vendor: Acme Supplies\nInvoice No: 1002\nDate: 2026-02-01\n"
    "Amount Due: $510.00\nAccount Number: NEW-999-888"
)


def test_resume_with_valid_token_after_pause():
    """Full HITL loop through the API: a bank-change invoice pauses, and a
    correctly signed token lets /resume proceed to a final decision."""
    upsert_vendor("Acme Supplies", bank_account="ACME-111-222", avg_amount=500.0)

    res = client.post("/analyze", data={"type": "invoice", "text": BANK_CHANGE_INVOICE})
    assert res.status_code == 200
    body = res.json()
    assert body["paused"] is True
    assert body["hitl_link"], "a signed approval link should be issued when paused"

    # The signal detail (old vs new account) must be present in the payload the GUI renders.
    sig = next(s for s in body["state"]["signals"] if s.get("reason") == "bank_account_changed")
    assert "ACME-111-222" in sig["detail"] and "NEW-999-888" in sig["detail"]

    q = parse_qs(urlparse(body["hitl_link"]).query)
    res2 = client.post(
        f"/resume/{body['trace_id']}",
        data={"approved": "false", "notes": "reject", "token_exp": q["exp"][0], "token_sig": q["sig"][0]},
    )
    assert res2.status_code == 200
    assert res2.json()["state"]["decision"] == "block"
