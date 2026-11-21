# Vinayak ProcureAI — real-data hackathon build

FastAPI + vanilla HTML/CSS/JavaScript application. No Node.js or frontend build is required. The supplied Vinayak data pack is included under `data_private/vinayak-vch3-data/` and is loaded automatically for the ERP catalogue and standard RFQ terms.

## Run locally (Windows PowerShell)

From the extracted repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
# Add SARVAM_API_KEY=your_key to .env. Required for live AI; without it the trace explicitly reports deterministic fallback.
$env:PYTHONPATH = "backend"
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs. Python 3.11 or 3.12 is recommended.

## Run locally (macOS / Linux)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
cp .env.example .env
export PYTHONPATH=backend
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

## Test the real Vinayak workflow

1. Click **Import Amara Tower-2 source records**. This imports the actual source email and BOQ, not a synthetic fixture. This loads the actual site email and Tower-2 quantity workbook from the included data pack.
2. Review the extracted BOQ rows and source evidence. The workbook parser selects the work-order item-wise BOQ sheet; validate the result against the original workbook.
3. Click Find ERP candidates. Sarvam semantically ranks candidates from the actual Vinayak ERP workbook; the application validates returned codes against the workbook. Manually select the correct code for each line. Near-duplicate codes require particular care.
4. Click **Generate RFQ text**. Sarvam drafts the vendor-facing message using the approved item schedule and six standard terms read from the supplied RFQ email. The application checks that controlled facts and all terms are preserved; review before sending anything to a vendor.
5. Upload the supplied quotation PDFs one at a time from `data_private/vinayak-vch3-data/06_quotations/`. Use the vendor names shown by the filenames: Bajrang Construction, Purvyakruti, S.K. Construction, and Shyama.
6. Generate the comparative statement. Check all extraction warnings, quantity/unit mismatches, GST basis and evidence. A scanned quotation may require OCR; do not treat OCR output as verified.
7. Generate the rule-based shortlist with a Sarvam-written management explanation. Ranking and eligibility remain deterministic; the AI explanation is advisory and cannot change the ranking. Record approval, override, or rejection only after a human reviews the underlying quotations.

The second site requirement (Aquina internal road work), its BOQ/drawing, contractor list, procurement SOP, and tender BOQ are also included as source material. The current quick-load workflow is specifically wired to the Amara waterproofing requirement because the four included vendor quotations relate to that tender. Aquina is available for a separate intake test by uploading its email and BOQ manually.

## Data handling — important

The supplied data README says these are real working documents shared only for the hackathon and must not be posted, shared outside the team, or retained afterwards; obtain Vinayak's permission before any portfolio use. The data is stored under `data_private/`, which is gitignored. **Do not commit, push, publish, or deploy this ZIP with the private data pack to a public repository or public hosting service.** The requested local build bundles the data for local testing only. Before public deployment, remove `data_private/` and arrange an authorised, access-controlled private data source. Do not expose real vendor rates, names, terms, contacts or documents in a public demo.

## AI configuration

`SARVAM_API_KEY` is required for live Sarvam calls. With a key, Sarvam chat interprets requirement emails, semantically ranks ERP catalogue candidates, drafts RFQ text and structures quotation extraction; Sarvam Document AI can parse scanned PDFs/images. Without a key or when Sarvam fails, the application falls back to deterministic parsing/matching and the AI traces explicitly identify that fallback. Cached/sample AI responses are disabled by default. AI extraction is not a source of truth: compare every field to the source document. The code does not claim that any AI extraction is verified.

## OCR requirements

Text-based PDFs are parsed with pdfplumber. Scanned PDFs/images use Sarvam Document AI when configured; otherwise local OCR is attempted. For reliable local OCR install Tesseract and Poppler and ensure both executables are on PATH. On Windows, install Tesseract OCR and Poppler separately.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Render/generic host build and start commands, environment variables, and private-data restrictions.

## Docker

```bash
docker build -t vinayak-procureai .
docker run --rm -p 8000:8000 --env-file .env vinayak-procureai
```

For public deployment, do not include the private data pack. Configure an authorised private storage/mount and set `DATA_PACK_DIR` to that mounted path. SQLite and uploaded files are ephemeral in a container unless a persistent disk is configured.

## API health

`GET /api/health` reports service/database status. `POST /api/procurement/import/amara-tower-2` imports the real Amara requirement and runs live Sarvam-backed intake and semantic ERP matching when `SARVAM_API_KEY` is configured. The synthetic demo endpoint has been removed from the application.
