from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from cyber_agent import config as cfg
from cyber_agent.api.vendor_service import API_KEY_HEADER, app
from cyber_agent.data.store import upsert_vendor

API_KEY = "test-key-123"
HEADERS = {API_KEY_HEADER: API_KEY}


@pytest_asyncio.fixture
async def client(isolated_db):
    object.__setattr__(cfg.settings, "vendor_api_key", API_KEY)
    # Starlette's sync TestClient is broken against httpx >= 0.28 (Client.__init__
    # no longer accepts the `app` kwarg), so drive the ASGI app directly.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_lookup_miss_returns_404(client):
    resp = await client.get("/vendors/nobody", headers=HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upsert_then_lookup_roundtrip(client):
    payload = {
        "supplier_id": "Acme Supplies",
        "bank_account": "ACME-111-222",
        "avg_amount": 500.0,
        "last_seen": "2026-01-10",
        "metadata": {"provider_id": "abc-123", "countries": ["US"]},
    }
    create = await client.post("/vendors", json=payload, headers=HEADERS)
    assert create.status_code == 200
    body = create.json()
    assert body["supplier_id"] == "Acme Supplies"
    assert body["bank_account"] == "ACME-111-222"
    assert body["avg_amount"] == 500.0
    assert body["last_seen"] == "2026-01-10"
    assert body["metadata"]["provider_id"] == "abc-123"

    fetched = (await client.get("/vendors/acme supplies", headers=HEADERS)).json()
    assert fetched["bank_account"] == "ACME-111-222"


@pytest.mark.asyncio
async def test_upsert_partial_update_preserves_existing_fields(client):
    upsert_vendor("Acme Supplies", bank_account="ACME-111-222", avg_amount=500.0)

    resp = await client.post(
        "/vendors",
        json={"supplier_id": "Acme Supplies", "bank_account": "NEW-999"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["bank_account"] == "NEW-999"
    assert body["avg_amount"] == 500.0


@pytest.mark.asyncio
async def test_missing_api_key_returns_401(client):
    resp = await client.get("/vendors/anything")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_api_key_returns_401(client):
    resp = await client.get("/vendors/anything", headers={API_KEY_HEADER: "wrong"})
    assert resp.status_code == 401
