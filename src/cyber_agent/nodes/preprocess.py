from __future__ import annotations

from ..preprocessing.email_parse import parse_email
from ..preprocessing.ocr import extract_invoice_fields
from ..state import ThreatState


def preprocess(state: ThreatState) -> dict:
    raw = state.get("raw_input") or {}
    content = raw.get("content")
    if content is None:
        return {"parsed": {}}

    email = parse_email(content)
    if email is None:
        return {"parsed": extract_invoice_fields(content)}

    # Invoice fields come from the body alone — the rendered blob prepends
    # headers and link targets, and those would shadow the real vendor/amount.
    parsed = extract_invoice_fields(email["body"])
    parsed["text"] = email["text"]
    parsed["email_sender"] = email["sender"]
    parsed["email_subject"] = email["subject"]
    parsed["email_links"] = len(email["links"])
    parsed["email_link_mismatch"] = any(link["mismatch"] for link in email["links"])

    updates: dict = {"parsed": parsed}
    # A sender typed into the form is the analyst's own assertion — keep it.
    if email["sender"] and not (raw.get("sender") or "").strip():
        updates["raw_input"] = {**raw, "sender": email["sender"]}
    return updates
