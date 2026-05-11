"""Vendor history HTTP service.

Exposes the SQLite-backed vendor table (`src/cyber_agent/data/store.py`)
as a small HTTP API guarded by an `X-API-Key` header. Can be imported
as an external tool via `vendor_api.yaml`.

Run:
    uvicorn cyber_agent.api.vendor_service:app --port 8001
"""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

from ..config import settings
from ..data.store import get_vendor, upsert_vendor

API_KEY_HEADER = "X-API-Key"

app = FastAPI(
    title="Protego Vendor Service",
    version="0.1.0",
    description="Vendor history lookup and upsert.",
)


class _VendorBase(BaseModel):
    supplier_id: str = Field(..., description="Supplier identifier (case-insensitive).")
    bank_account: str | None = Field(None, description="Last known bank account on file.")
    avg_amount: float | None = Field(None, description="Historical average invoice amount.")
    last_seen: str | None = Field(None, description="ISO date of the most recent invoice.")


class VendorRecord(_VendorBase):
    metadata: dict[str, Any] = Field(default_factory=dict, description="Free-form attributes.")


class VendorUpsertRequest(_VendorBase):
    metadata: dict[str, Any] | None = None


def require_api_key(x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER)) -> None:
    expected = settings.vendor_api_key
    if not expected or not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.get(
    "/vendors/{supplier_id}",
    response_model=VendorRecord,
    operation_id="lookup_vendor",
    summary="Look up a vendor by supplier ID",
    dependencies=[Depends(require_api_key)],
)
def lookup_vendor(supplier_id: str) -> VendorRecord:
    record = get_vendor(supplier_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"vendor not found: {supplier_id}")
    return VendorRecord(**record)


@app.post(
    "/vendors",
    response_model=VendorRecord,
    operation_id="upsert_vendor",
    summary="Create or update a vendor record",
    dependencies=[Depends(require_api_key)],
)
def upsert_vendor_endpoint(payload: VendorUpsertRequest) -> VendorRecord:
    record = upsert_vendor(
        supplier_id=payload.supplier_id,
        bank_account=payload.bank_account,
        avg_amount=payload.avg_amount,
        last_seen=payload.last_seen,
        metadata=payload.metadata,
    )
    return VendorRecord(**record)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("cyber_agent.api.vendor_service:app", host="0.0.0.0", port=8001, reload=False)
