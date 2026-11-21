# ARCHITECTURE

Principle: **separate what is read, what is understood, what is computed, and what is decided.**

```
 Browser (React/Vite)
        │  REST + JSON (multipart for uploads)
        ▼
 ┌─────────────── FastAPI (backend/app) ────────────────┐
 │ api/        thin handlers; contract enforced by Pydantic
 │    │
 │ services/   orchestration: the ONLY layer that combines the four below
 │    ├── document/     READ    PDF/Excel text, tables, OCR     (deterministic)
 │    ├── ai/           UNDERSTAND  gateway -> Sarvam / fallback / cache; Pydantic-validated
 │    ├── procurement/  COMPUTE  ERP candidates, normalise, compare, shortlist (deterministic, Decimal)
 │    └── database/     REMEMBER SQLite (JSON documents)
 │ core/       settings from env, error envelope
 │ schemas/    shared Pydantic models = the API contract in code
 └───────────────────────────────────────────────────────┘
        Human decision = POST /api/approvals/{id}  (nothing auto-selects a vendor)
```

## Components and responsibilities

| Component | Owner | Responsibility | Must not |
|---|---|---|---|
| `frontend/` | M1 | UI for the 6 steps, show flags/evidence/AI traces, mock mode | Compute money; call anything but `/api` |
| `api/` | M2 | Routes, request validation, status codes | Contain business logic |
| `schemas/` | M2 | Single definition of every request/response/AI-output shape | Import other app packages |
| `services/` | M2 | Per-step workflows; persist; assemble traces | Do arithmetic on money |
| `ai/` | M2 | Gateway: cache -> primary -> one repair -> fallback; traces | Be called from anywhere but `services/` |
| `core/` | M2 | Env config, error handlers | Hold secrets in code |
| `document/` | M3 | Extract text/tables/pages + evidence pointers; OCR | Call an LLM; "correct" numbers |
| `procurement/` | M3 | ERP candidate generation, normalisation, comparison, shortlist rules | Call an LLM; resolve mismatches itself |
| `database/` | M3 | SQLite schema + access | Hold logic |
| `tests/`, `docs/` | M3 | Quality gate, fixtures, workflow docs | Contain real data |

Layer rules are enforced by `tests/test_architecture_rules.py`.

## Data flow (happy path)

1. **Intake** `POST /requirements/intake`: BOQ Excel parsed by `document` (quantities come from cells, not from an LLM).
   `ai` turns the email (and optional Hindi/Bengali note) into project/scope/summary. -> `requirement_id`.
2. **Match** `POST /requirements/match`: `procurement.erp_candidates` produces a lexical shortlist + near-duplicate warnings
   from the ERP catalogue; `ai` may only re-rank/explain those candidates (it cannot invent codes). Human confirms codes.
3. **RFQ** `POST /rfq/generate`: template renders items, quantities and the six terms. LLM use optional (cover note wording only).
4. **Quotations** `POST /quotations/upload` (x4): `document` extracts text/OCR; `ai` structures it to `QuotationResponse`;
   every value keeps `SourceEvidence`. No totals computed here.
5. **Comparison** `POST /comparisons/generate`: `procurement.build_comparison` (pure Decimal) aligns lines to RFQ lines,
   compares units/quantities, computes `rfq_qty x rate`, applies GST basis, diffs terms, emits flags.
   Mismatches become `needs_review` and are excluded from totals until a human `UnitResolution` is submitted (re-POST with `resolutions`).
6. **Shortlist** `POST /comparisons/{id}/shortlist`: rule-based; fully comparable vendors ranked by total incl. GST;
   vendors with unresolved lines or unstated GST go to `pending_review`; blocking flags -> `excluded`. Every reason links evidence.
7. **Approval** `POST /approvals/{id}`: human approves / overrides (reason mandatory) / rejects all. Approval note is a template over stored facts.

## AI gateway policy (ai/gateway.py)

cache hit -> return; else for each provider (Sarvam, then fallback): call with timeout -> validate with Pydantic ->
on invalid output ONE repair attempt showing the validation error -> on provider error go to next provider.
Everything failing raises `AI_PROVIDER_UNAVAILABLE` / `AI_OUTPUT_INVALID`; nothing is fabricated.
Every attempt yields an `AITrace` that is returned to the UI.
Implemented and unit-tested with fake providers only. **Real providers are not implemented** (UNKNOWN API details).

## Key decisions (and what we deliberately did NOT do)

| Decision | Why |
|---|---|
| SQLite, stdlib `sqlite3`, JSON blobs per document | One container, zero setup. No ORM, no migrations: the Pydantic models are the schema. |
| Sync handlers (`def`), no task queue | FastAPI runs them in a threadpool; extraction takes seconds; a queue is overhead we can't afford today. |
| No auth, no multi-tenant | Out of scope. `approver_name` is free text. |
| Frontend: plain React, `fetch`, no router/state/UI library | Six steps fit one page with sections. Zero extra dependencies. |
| One container serves the built SPA | Same origin, one Render service, no CORS in prod. |
| Pricing on the RFQ quantity (`rfq_qty x rate`) | Makes vendors comparable. Vendor's own quantity and amount are shown beside it. **ASSUMPTION**, see mentor questions. |
| GST unstated => total is `null` (UNKNOWN) | Never guess a tax basis. |
| Shortlist = lowest total among fully comparable vendors, plus visible caveats | No hidden weights, no invented vendor scores (we have no performance data). |
| Mocks validated against schemas in CI | UI can be built without the backend and cannot silently drift. |

## Deployment

Single `Dockerfile` (multi-stage: Node builds the SPA, Python image serves API + static files on `$PORT`).
Render: *New Web Service -> Docker -> repo -> set env vars from `.env.example` -> health check path `/api/health`*.
Railway fallback: same Dockerfile, set the same variables. SQLite lives on ephemeral disk (demo only).
