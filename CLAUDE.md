# Protego Cyber Agent

Multi-agent LangGraph app for small-business AI threat defense. Classifies email / PDF / invoice input, routes to a specialist agent (invoice, phishing, BEC), scores risk, and takes Alert / Block / Verify action with HITL.

## Architecture

Single `StateGraph` over `ThreatState` (src/cyber_agent/state.py). Flow:

```
START → preprocess → orchestrator ─┬─► invoice_agent ─┐
                                    ├─► phishing_agent ┼─► risk_scoring → action → feedback_logger → END
                                    └─► bec_agent ─────┘
```

- **Orchestrator** routes via `Command(update=..., goto=...)` (src/cyber_agent/nodes/orchestrator.py).
- **Signals** use an `operator.add` reducer so agents (and future `Send` fan-out) can append without clobbering.
- **HITL** uses `interrupt()` inside `nodes/action.py`; resumed with `Command(resume=...)` via `POST /resume/{thread_id}`.
- **Checkpointer**: `SqliteSaver` by default, `MemorySaver` fallback. Thread id == trace id.
- **LLM**: `make_llm(agent)` in `llm.py` returns a `_GeminiLLM` wrapper around `ChatGoogleGenerativeAI` (`gemini-2.0-flash` default) or a deterministic `_StubLLM` when `GEMINI_API_KEY` is missing — tests and local dev work offline.

## Layout

```
src/cyber_agent/
  config.py          # env + settings dataclass
  state.py           # ThreatState TypedDict + reducers
  llm.py             # make_llm / make_embeddings (+ stubs)
  graph.py           # build_graph()
  hitl_mailer.py     # HMAC-signed approval links, SMTP
  preprocessing/ocr.py
  preprocessing/email_parse.py  # .eml → body text + real <a href> targets
  nodes/             # preprocess, orchestrator, invoice_agent,
                     # phishing_agent, bec_agent, risk_scoring,
                     # action, feedback_logger
  tools/             # vendor_lookup, safe_browsing, urlscan, email_baseline
  rag/               # embeddings, retriever (in-memory cosine)
  data/store.py      # vendors / audit_log / signatures (SQLite)
  api/main.py        # FastAPI: /analyze, /hitl/{tid}, /resume/{tid}
tests/               # pytest, run with `python -m pytest`
```

## Running

```bash
pip install -e .[dev]
cp .env.example .env         # fill GEMINI_API_KEY to leave stub mode
uvicorn cyber_agent.api.main:app --reload
curl -F text="Vendor: Acme..." http://localhost:8000/analyze
python -m pytest
```

Container: `docker build -t protego . && docker run -p 8000:8000 protego`.

## Conventions

- **Nodes return partial state dicts** — never mutate in place. Use `signals` (list reducer) to append evidence; other fields overwrite.
- **Decisions**: `pass` / `alert` / `block` / `verify`. Any signal with `force: "verify"` short-circuits `risk_scoring` to `verify`.
- **Trace id** is the thread id — reuse it for checkpointer config and audit log.
- **Stub fallback is the contract**: any new external dependency must degrade gracefully when credentials are absent so the test suite stays offline.
- **Add a test per node behavior change**, not per file. Fixtures live inline in `tests/` — the four invoice scenarios (known-good, bank-change, new-vendor, amount-anomaly) are the regression baseline.
- **`.eml` input is parsed, pasted text is not.** `preprocess` routes MIME input through `parse_email` (strict header gate — pasted text opening with `From:`/`Subject:` stays plain text). `parsed["text"]` then leads with `SENDER:`/`SUBJECT:` and a `LINK TARGETS` block; those labels deliberately avoid the RFC field names because `extract_invoice_fields` matches `/vendor|from/` and takes the first hit. Invoice fields are extracted from the body alone for the same reason. A recovered anchor whose display text names a different domain than its href sets `parsed["email_link_mismatch"]`, which outranks the orchestrator's invoice keywords so invoice-shaped phishing still reaches the URL analysis.

## Gemini notes

- Default model: `gemini-2.0-flash`. Override per agent via `make_llm(agent, model_id=...)`.
- Embeddings default: `models/text-embedding-004`.
- `_GeminiLLM` wraps `ChatGoogleGenerativeAI` so `.invoke()` returns a plain string (matching `_StubLLM`).
- Vector store: `rag/retriever.py` is in-memory and swappable without touching callers.
- HITL channel: email approval link. `/hitl/{thread_id}?exp=&sig=` renders Approve/Reject; posts back to `/resume` with HMAC-verified token.
