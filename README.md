# Vinayak ProcureAI

AI-assisted procurement **decision support** for construction procurement: requirement emails and BOQs in, evidence-backed
comparative statement out. A human makes the final decision. Built for Vibe Coders Hackathon 3 (Kolkata, 21 Nov 2026).

> Status: architecture + minimal working skeleton. Only `GET /api/health` is functional; other endpoints validate input and return `501`.
> Read [CONTEXT.md](CONTEXT.md) first, then [ARCHITECTURE.md](ARCHITECTURE.md) and [API_CONTRACT.md](API_CONTRACT.md).

## Stack

React + Vite · FastAPI · Pydantic v2 · SQLite · Sarvam AI (primary, unverified) + fallback provider · one Docker container.

## Dependencies (approved list: no additions without approval)

- Backend runtime: `fastapi`, `uvicorn`, `pydantic`, `python-multipart` (uploads), `httpx` (AI provider HTTP calls)
- Backend dev: `pytest`
- Frontend: `react`, `react-dom`; dev: `vite`, `@vitejs/plugin-react`
- **Proposed, NOT installed (needs approval, Member 3 to justify):** an Excel reader (`openpyxl`), a PDF text/table reader (`pdfplumber` or `pypdf`), OCR (`pytesseract` + system Tesseract, or LLM vision).

## Setup and run

Prerequisites: Python 3.13, Node 22+.

```bash
git config core.hooksPath .githooks        # guard: forbidden files + 16:45 IST commit cutoff
cp .env.example .env                       # fill locally; never commit

# Backend (terminal 1)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend && npm install && npm run dev  # http://localhost:5173 (proxies /api -> :8000)
# UI without a backend:  VITE_USE_MOCKS=true npm run dev

# Tests (from repo root)
python -m pytest -q
```

Check: `curl localhost:8000/api/health`, interactive docs at `http://localhost:8000/docs`.

## Docker (production-like)

```bash
docker build -t vinayak-procureai .
docker run --rm -p 8000:8000 --env-file .env vinayak-procureai   # UI + API at http://localhost:8000
```

Deploy on Render: New Web Service -> Docker -> this repo -> add the env vars from `.env.example` -> health check path `/api/health`.
Railway fallback: same Dockerfile and variables. Note the SQLite file is on ephemeral disk.

## Repository layout and ownership

```
frontend/                     Member 1
backend/app/api,schemas,services,ai,core, main.py    Member 2
backend/app/document,procurement,database, tests/, docs/   Member 3
root docs, Dockerfile, .gitignore, .env.example      Member 3 (root maintainer)
```

## Data handling (important)

The hackathon data pack contains **real Vinayak documents**. Keep it outside this repo (it is gitignored by name). Use only
synthetic fixtures (`tests/fixtures/synthetic_*`). Do not paste real content into samples, mocks, tests or docs.
Delete local copies after the event as the data owner requested.
