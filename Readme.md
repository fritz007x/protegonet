# Protegonet — Cyber Agent

AI threat defense for small and rural businesses. A multi-agent [LangGraph](https://langchain-ai.github.io/langgraph/) application that ingests email / PDF / invoice content, classifies the threat, runs specialist analysis, scores risk, and takes one of three actions — **Alert / Block / Verify** — with a human-in-the-loop escape hatch for high-risk events.

## Why

Small businesses are the soft underbelly of the AI-attack era: GenAI-crafted phishing, business-email-compromise (BEC), and invoice fraud now reach the same inboxes that have no SOC, no SIEM, and no threat-intel budget. Protegonet brings an orchestrated agent pipeline — defense with the same tools the attackers are using — to organizations that can't staff one.

## Features

- **Multi-agent orchestration** — single `StateGraph` with dynamic `Command(goto=...)` routing to specialist agents (invoice, phishing, BEC).
- **Invoice fraud detection** — OCR + vendor history + LLM reasoning. Hard rule: bank-account change → always HITL verify.
- **Phishing analysis** — URL extraction, Google Safe Browsing + urlscan.io lookups, suspicious-TLD and display-name heuristics.
- **BEC detection** — urgency-language rules, sender baseline checks, RAG over known BEC patterns with Gemini embeddings.
- **Risk scoring + action** — weighted severity aggregation; `verify` decisions pause the graph via `interrupt()` and emit an HMAC-signed email approval link.
- **Durable state** — SqliteSaver checkpointer (local) / Postgres-backed in prod; paused runs resume on the same thread id.
- **Gemini-powered** — `gemini-2.0-flash` by default, swappable per agent via `make_llm(agent, model_id=...)`.
- **Offline-safe fallbacks** — stub LLM / embeddings / API clients so the test suite runs without credentials.

## Architecture

```
                  ┌────────────────────┐
 input (API /     │  Preprocessing     │
 file upload) ──▶ │  OCR + parsing     │
                  └─────────┬──────────┘
                            ▼
                  ┌────────────────────┐
                  │ Orchestrator Node  │  classify + route
                  └─────┬────┬────┬────┘
                        ▼    ▼    ▼
                  ┌──────┐┌──────┐┌──────────┐
                  │Phish ││ BEC  ││ Invoice  │
                  └───┬──┘└───┬──┘└────┬─────┘
                      ▼       ▼        ▼
                  ┌────────────────────┐
                  │ Risk Scoring Node  │  aggregate → score
                  └─────────┬──────────┘
                            ▼
                  ┌────────────────────┐
                  │ Action Node        │  Alert / Block / Verify (interrupt)
                  └─────────┬──────────┘
                            ▼
                  ┌────────────────────┐
                  │ Feedback Logger    │  → SQLite audit_log
                  └────────────────────┘
```

- Shared `ThreatState` (TypedDict) with an `operator.add` reducer on `signals` so multiple agents (and future `Send` fan-out) append without clobbering.
- HITL uses graph-native `interrupt()` + `Command(resume=...)`. No external queue.

## Project Layout

```
cyber-agent/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── src/cyber_agent/
│   ├── config.py              # env + Settings dataclass
│   ├── state.py               # ThreatState + reducers
│   ├── llm.py                 # Gemini LLM / embeddings factory (+ stubs)
│   ├── graph.py               # build_graph() — StateGraph wiring
│   ├── hitl_mailer.py         # HMAC-signed approval links + SMTP
│   ├── preprocessing/ocr.py
│   ├── nodes/
│   │   ├── preprocess.py
│   │   ├── orchestrator.py    # Command(goto=...) routing
│   │   ├── invoice_agent.py
│   │   ├── phishing_agent.py
│   │   ├── bec_agent.py
│   │   ├── risk_scoring.py
│   │   ├── action.py          # interrupt() on verify
│   │   └── feedback_logger.py
│   ├── tools/
│   │   ├── vendor_lookup.py
│   │   ├── safe_browsing.py
│   │   ├── urlscan.py
│   │   └── email_baseline.py
│   ├── rag/
│   │   ├── embeddings.py
│   │   └── retriever.py       # in-memory cosine similarity
│   ├── data/store.py          # vendors / audit_log / signatures (SQLite)
│   └── api/main.py            # FastAPI: /analyze, /hitl/{tid}, /resume/{tid}
└── tests/
    ├── test_invoice_agent.py
    ├── test_orchestrator_phishing.py
    ├── test_bec_rag.py
    └── test_hitl_hardening.py
```

## Getting Started

### Requirements

- Python 3.10+
- (Optional) Tesseract + Poppler for real PDF OCR. Without them, text input still works.
- (Optional) Gemini API key. Without it, the app runs against deterministic stubs — useful for tests and local dev.

### Install

```bash
pip install -e .[dev]
cp .env.example .env
# edit .env — fill GEMINI_API_KEY to leave stub mode
```

### Run the API

```bash
uvicorn cyber_agent.api.main:app --reload
```

Endpoints:

- `POST /analyze` — multipart `file=` (PDF) or form `text=`. Returns `{trace_id, paused, hitl_link, state}`.
- `GET  /hitl/{thread_id}?exp=&sig=` — Approve / Reject page (HMAC-verified).
- `POST /resume/{thread_id}` — form `approved=true|false`, `notes=...` (optionally `token_exp` + `token_sig`).

Example:

```bash
curl -F text="Vendor: Acme Supplies
Invoice No: 1002
Amount Due: \$510.00
Account Number: NEW-999-888" \
  http://localhost:8000/analyze
```

### Run tests

```bash
python -m pytest
```

The suite is offline-safe — it exercises the whole graph including HITL interrupt/resume, the RAG retriever, and HMAC link signing, all without hitting any external API.

### Vendor service

A separate FastAPI service exposes the SQLite vendor history as a tool importable via `vendor_api.yaml`. It shares the same `audit.sqlite` store as the LangGraph app.

```bash
# 1. Set an API key the client will send.
echo "VENDOR_API_KEY=change-me" >> .env

# 2. Seed the vendor table from the bundled invoices fixture.
python scripts/seed_vendors.py

# 3. Run the service on its own port.
uvicorn cyber_agent.api.vendor_service:app --port 8001

# 4. Smoke test.
curl -H "X-API-Key: change-me" http://localhost:8001/vendors/vendor-969284fc
```

## Configuration

All config is loaded from `.env` via `src/cyber_agent/config.py`. Key variables:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Gemini API key (absent → stub mode) |
| `GEMINI_MODEL_ID` | Default `gemini-2.0-flash` |
| `GEMINI_EMBEDDING_MODEL_ID` | Default `models/text-embedding-004` |
| `SAFE_BROWSING_KEY`, `URLSCAN_KEY` | External threat intel (optional) |
| `SMTP_*`, `HITL_APPROVER_EMAIL` | HITL email delivery (optional; falls back to logging link) |
| `HITL_SIGNING_KEY`, `HITL_LINK_TTL_MINUTES`, `HITL_PUBLIC_BASE_URL` | Approval-link signing |
| `SQLITE_CHECKPOINT_PATH`, `AUDIT_DB_PATH` | Local persistence paths |
| `VENDOR_API_KEY` | Shared secret for the vendor service |

## Deployment

The app is packaged as a FastAPI service and containerized via `Dockerfile` (Python 3.11-slim + Tesseract + Poppler).

```bash
docker build -t protegonet .
docker run -p 8000:8000 --env-file .env protegonet
```

## Development Notes

Conventions (node return shape, signal reducer, stub-fallback contract, test baseline):

- Nodes return partial state dicts; never mutate.
- Any signal with `force: "verify"` short-circuits risk scoring.
- New external deps must degrade gracefully when credentials are absent.
- Trace id == thread id == audit key.

## License

TBD.
