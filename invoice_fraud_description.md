 ▐▛███▜▌   Claude Code v2.1.119
▝▜█████▛▘  Sonnet 4.6 · Claude Pro
  ▘▘ ▝▝    ~\Documents\PROJECTS\CYBER AGENT

❯ Generate a good description of the invoice fraud detection agent, including   
  its purpose, tools, and agents, to help other agents know when to use it.     

● Let me read the invoice agent and related files to write an accurate
  description.

  Searched for 1 pattern, read 4 files (ctrl+o to expand)

● Here is a description suitable for use as agent metadata, a docstring, or
  routing documentation:

  ---
  Invoice Fraud Detection Agent

  Purpose

  Analyzes incoming invoices to detect financial fraud before payment is
  approved. It combines deterministic rule-based checks against a vendor history
   database with an LLM-powered five-step Chain of Thought analysis, producing
  structured risk signals and a final FRAUDULENT / LEGITIMATE classification.

  When to route here

  The orchestrator sends input to this agent when:
  - The caller explicitly sets type: "invoice", or
  - The preprocessed text contains invoice-domain keywords: invoice, amount due,
   account number, bill to.

  What it checks

  1. New vendor — If the vendor has no prior record in the vendor database, a
  medium severity signal is raised. First-time suppliers warrant extra scrutiny.
  2. Bank account change — If the incoming bank account differs from the stored
  record for a known vendor, a high severity signal is raised with force: 
  "verify", which short-circuits risk scoring and escalates directly to
  Human-in-the-Loop (HITL) review. This is the primary Business Email Compromise
   payment-redirect indicator.
  3. Amount anomaly — If the invoice amount exceeds twice the vendor's
  historical average, a medium severity signal is raised.
  4. LLM deep analysis — After rule checks, the agent invokes the Granite LLM
  (or stub in offline mode) with a structured prompt that walks through: vendor
  identity and impersonation risk, payment detail discrepancies, document
  structure integrity, historical billing pattern comparison, and a final
  weighted assessment.

  Data and tools

  ┌────────────────────────┬────────────────────────────────────────────────┐
  │   Tool / Data source   │                      Role                      │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │                        │ Reads stored vendor record (bank account, avg  │
  │ get_vendor(name)       │ amount, last seen) from the vendor table —     │
  │                        │ SQLite in dev, watsonx.data in production      │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ lookup_vendor          │ Exposes get_vendor for tool-calling agents     │
  │ (LangChain tool)       │                                                │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │ remember_vendor        │ Creates or updates a vendor record after human │
  │ (LangChain tool)       │  verification; used post-HITL to keep the      │
  │                        │ baseline current                               │
  ├────────────────────────┼────────────────────────────────────────────────┤
  │                        │ Returns a WatsonxLLM (default                  │
  │ make_llm("invoice")    │ ibm/granite-4-h-small) or a deterministic stub │
  │                        │  when credentials are absent                   │
  └────────────────────────┴────────────────────────────────────────────────┘

  Outputs (partial state updates)

  ┌─────────────┬────────────────────────────────────────────────────────────┐
  │    Field    │                           Value                            │
  ├─────────────┼────────────────────────────────────────────────────────────┤
  │ signals     │ Appended list of {source, severity, reason, detail,        │
  │             │ [force]} dicts                                             │
  ├─────────────┼────────────────────────────────────────────────────────────┤
  │ reasoning   │ Full LLM Chain of Thought response (or error message)      │
  ├─────────────┼────────────────────────────────────────────────────────────┤
  │ threat_type │ "invoice"                                                  │
  └─────────────┴────────────────────────────────────────────────────────────┘

  Escalation behavior

  Any signal carrying force: "verify" (currently only bank_account_changed)
  bypasses automated risk scoring and triggers HITL via an HMAC-signed email
  approval link. All other signals flow to risk_scoring for numeric scoring and
  threshold-based action selection (pass / alert / block / verify).

  Do not use this agent for

  - Phishing emails or suspicious URLs → route to phishing_agent
  - Wire transfer requests, gift card demands, or executive impersonation with
  no invoice document → route to bec_agent

✻ Cogitated for 33s

※ recap: Generated a description of the invoice fraud detection agent covering its routing logic, rule-based checks, LLM analysis, tools, and outputs. No code was changed. Next step: integrate this description into the codebase as a docstring or metadata if desired. (disable recaps in /config)