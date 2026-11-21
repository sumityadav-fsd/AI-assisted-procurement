# Vinayak ProcureAI — local MVP

Single FastAPI process serving a plain HTML/CSS/vanilla-JS interface. No React, Vite, Node runtime, or frontend build.

## Run locally (Windows PowerShell)

From repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
# Put SARVAM_API_KEY in .env if available. No key is required for synthetic demo mode.
cd backend
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. API docs: http://localhost:8000/docs.

## Apply the review patch to your clone

Clone the architecture branch and create the local build branch:

```powershell
git clone --branch architecture/initial-skeleton https://github.com/sumityadav-fsd/AI-assisted-procurement.git
cd AI-assisted-procurement
git switch -c mvp/build
```

Extract the review ZIP beside the clone (the folder will be named `VinayakProcureAI-ReviewBuild`), then run its script:

```powershell
cd ..\VinayakProcureAI-ReviewBuild
.\apply_to_repo.ps1 -RepoPath ..\AI-assisted-procurement
cd ..\AI-assisted-procurement
```

The script only copies files; it does not stage, commit, push or merge. Inspect `git status` and review every change yourself.

Enable the deadline/private-data guard once per clone:

```powershell
git config core.hooksPath .githooks
```

Run tests from repo root:

```powershell
$env:PYTHONPATH="backend"
python -m pytest -q
```

## Private Vinayak data

Extract the supplied data pack into `data_private/vinayak-vch3-data/` at repository root. This directory is gitignored. Never commit the ZIP, extracted files, derived real-data caches, vendor names, rates, or terms. The application loads the ERP workbook and RFQ terms from this private runtime directory. `ERP_CATALOGUE_PATH` can point to a different private catalogue workbook. If absent, those values remain UNKNOWN. `AI_SAMPLES_DIR` defaults to `data_private/ai_samples` so any real-data-derived cache remains private.

## AI

Sarvam chat uses the documented `POST https://api.sarvam.ai/v2/chat/completions` endpoint, `api-subscription-key` header and `sarvam-105b` model for text. Scanned PDFs/images use Sarvam Document AI Parse (`POST /doc-ai/v1/job/parse` plus documented status and download-url calls) when a key is configured. Set only `SARVAM_API_KEY` in `.env`.

With a key, Sarvam structures quotation text into a Pydantic-validated extraction schema; it is instructed only to transcribe, never calculate. Without a key, email structuring and quotation extraction use deterministic parsing; Hindi/Bengali notes are retained unchanged with translation marked unavailable. The synthetic demo works offline. No fallback provider is configured. AI calls have one retry/repair; deterministic parsing precedes the private cache.

## Scanned PDFs

Text PDFs are parsed with pdfplumber. Sparse/scanned PDFs and images use Sarvam Document AI Parse when a key is configured. Otherwise local Tesseract OCR is attempted when the Docker image is built with `--build-arg INSTALL_OCR=true` (Poppler is included for PDFs). OCR accuracy must be reviewed; unreadable values remain UNKNOWN.

## Comparison rules

All financial calculations use Python Decimal. Quoted quantity/unit mismatches are blocking and excluded from totals until a human submits a UnitResolution with factor, reviewer and reason. GST basis/rate unknown => total UNKNOWN. Arithmetic checks compare quoted quantity × quoted rate against stated amount.

## Docker / Render

```bash
docker build -t vinayak-procureai .
docker run --rm -p 8000:8000 --env-file .env vinayak-procureai
```

Optional OCR tools:

```bash
docker build --build-arg INSTALL_OCR=true -t vinayak-procureai .
```

Render: create a Web Service from the public repository, choose Docker, set `SARVAM_API_KEY` if available, set health check path `/api/health`, and deploy. SQLite and uploads use the container filesystem; without a persistent disk they are ephemeral and may be lost on redeploy. For a short demo, use Load demo data after each fresh deployment.

## Scope / limitations

The eight procurement endpoints are implemented as an MVP, plus `/api/demo/load`. Vendor extraction is heuristic and must be reviewed; line matching is conservative. No real-data extraction result or live Sarvam call is claimed as verified unless run with the user's key in their environment.
