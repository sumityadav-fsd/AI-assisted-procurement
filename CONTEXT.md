# CONTEXT: Vinayak ProcureAI

Single source of truth for anyone (human or AI assistant) starting work in this repo. Read this first.

- **Event:** Vibe Coders Hackathon 3, Kolkata, 21 Nov 2026. **No commits after 16:45 IST.**
- **Goal:** a working, demonstrable MVP, not an enterprise platform. When in doubt, cut scope.
- **Root-docs maintainer:** **Member 3** (CONTEXT, ARCHITECTURE, API_CONTRACT, README, Dockerfile, `.gitignore`, `.env.example`, `.githooks/`, `pytest.ini`). Everyone else *requests* changes to these files from Member 3 (a chat message is enough).

## 1. Product

AI-assisted procurement **decision support** for construction procurement. It turns site requirement emails and BOQs into
structured requirements, matches them to ERP item codes, drafts RFQs, extracts vendor quotations and produces an
evidence-backed comparative statement. **A human makes the final decision.**

Six features: (1) requirement intake, (2) ERP item matching, (3) RFQ generator (six standard terms), (4) quotation
intelligence (4 quotes, different layouts, one scan), (5) comparative statement, (6) management decision (rule-based
shortlist, reasons, evidence, approval note, human override).

**Out of scope:** authentication, real ERP integration, vendor registration, work orders, autonomous vendor selection,
historical vendor performance scoring.

## 2. Architecture in one paragraph

React SPA -> REST/JSON -> FastAPI. Four strictly separated layers: **document extraction** (`document/`) ->
**AI structuring** (`ai/`, behind one gateway) -> **deterministic evaluation** (`procurement/`) -> **human decision**
(approvals endpoint). Money and quantities are `Decimal` and only ever computed by deterministic code. Details:
[ARCHITECTURE.md](ARCHITECTURE.md). Endpoints: [API_CONTRACT.md](API_CONTRACT.md).

## 3. Non-negotiable rules

1. An LLM never calculates totals and never changes a quantity or unit.
2. Quantity/unit mismatches are **never** silently resolved: flag them; only a human `UnitResolution` clears one.
3. All AI output and all API I/O are validated with Pydantic. One repair retry, request timeout, fallback provider, cached samples.
4. AI traces (provider, status, latency, errors) are returned to the UI.
5. Secrets only in environment variables. `.env` is never committed.
6. **No real company data in the repo, ever.** Fixtures are synthetic. The hackathon data pack stays outside the repo.
7. Mark assumptions `ASSUMPTION` and unknowns `UNKNOWN`. Do not invent vendor ratings, performance, terms or quotation data.
8. No new dependencies without team-lead approval (see the approved list in README).

## 4. Team ownership (strict)

| Owner | Role | Owns exclusively |
|---|---|---|
| **Member 1** | Product, frontend, integration | `frontend/` |
| **Member 2** | Backend, AI, LLM gateway | `backend/app/api/`, `schemas/`, `services/`, `ai/`, `core/`, plus `backend/app/main.py`, `backend/requirements*.txt` |
| **Member 3** | Data, QA, parsing, deployment, root docs | `backend/app/document/`, `procurement/`, `database/`, `tests/`, `docs/`, and root files listed above |

Never edit another member's files. Ask them. Shared interfaces are the Pydantic schemas (Member 2) and
`document/interfaces.py` + `procurement/interfaces.py` (Member 3).

**Contract-change protocol:** Member 2 changes a schema -> tells the others in chat -> Member 3 updates `API_CONTRACT.md` ->
Member 1 regenerates/edits `frontend/src/mocks/*.json`. `tests/test_frontend_mocks.py` fails if a mock no longer matches the schema,
which is the alarm that something drifted.

*Note:* the initial skeleton in `frontend/` and `backend/` was created by the tech lead in one pass; from the first commit on,
ownership above applies.

## 5. Conventions

- Python 3.13, type hints, Pydantic v2 (`extra="forbid"`). Money/quantity: `Decimal`, JSON as strings.
- Layering imports (enforced by `tests/test_architecture_rules.py`): `procurement` and `document` never import `ai`; `schemas` imports nothing else;
  only `services` orchestrates across layers.
- Errors: always the envelope `{"error": {"code","message","details","request_id"}}`.
- IDs: opaque strings, prefixed (`req_`, `rfq_`, `quo_`, `cmp_`, `apr_`).
- Branches: `architecture/*`, then `m1/*`, `m2/*`, `m3/*`; small PRs into `main`. Never commit `.env`, data, or `*.db`.
- Enable the guard hook once: `git config core.hooksPath .githooks` (blocks forbidden files and commits after 16:45 IST on 21 Nov).

## 6. Status (update as you go: Member 3)

| Area | State |
|---|---|
| Repo skeleton, contract, schemas, error envelope | Done (this branch) |
| `/api/health` | Working |
| Other 7 endpoints | Validate input, then return `501 NOT_IMPLEMENTED` |
| AI gateway control flow (cache, repair, fallback) | Implemented and unit-tested with **fake** providers |
| Sarvam / fallback provider calls | **Not implemented, never called, UNKNOWN API details** |
| Document parsing, OCR, ERP matching, comparison, shortlist | Interfaces only |
| Frontend | Health page + synthetic mock fixtures |
| Docker | Written; see ARCHITECTURE/README for what was verified |

## 7. Known issues / risks

- **Real data vs external AI:** sending Vinayak's real documents to Sarvam or a fallback provider needs permission (docs/mentor_questions.md #1).
- Cached samples derived from real documents must live in a gitignored folder (`AI_SAMPLES_DIR`), not in the repo.
- Render free tier has an ephemeral disk: SQLite data is lost on redeploy. Acceptable for a demo; seed on startup.
- OCR for the scanned quotation (Tesseract vs LLM vision) is undecided; Dockerfile has an opt-in build arg only.
- Sarvam API specifics and the fallback provider choice are UNKNOWN.
