# Architecture — single FastAPI process

Browser static page (`backend/app/static/`) -> REST API -> `services/` orchestration -> four isolated layers:
`document/` reads PDF/Excel and evidence; `ai/` uses Sarvam via httpx and a trace/retry gateway; `procurement/` does lexical ERP matching and Decimal comparison; `database/` persists JSON records in SQLite. Human decisions enter only through approvals.

Layer rules: document and procurement never import AI or services; AI never imports domain layers; schemas are standalone; API routes do not contain document, AI or procurement logic. `tests/test_architecture_rules.py` enforces this.

No React, Node, separate worker, external database or authentication. One Uvicorn process and one Dockerfile.

## AI details verified from official Sarvam documentation

- Text structuring and quotation extraction: `POST https://api.sarvam.ai/v2/chat/completions`, header `api-subscription-key`, model `sarvam-105b`, Structured Outputs via `response_format.json_schema`.
- Scanned quotation OCR: Sarvam Document AI Parse uses multipart `POST /doc-ai/v1/job/parse`, polls `GET /doc-ai/v1/job/{job_id}/status`, obtains `GET /doc-ai/v1/job/{job_id}/download-url`, then downloads the returned ZIP. It is attempted before local Tesseract/Poppler for sparse PDF pages and images. No undocumented route is used.


## Cache and data boundary

Structured Sarvam responses are cached under `AI_SAMPLES_DIR`, defaulting to gitignored `data_private/ai_samples`. The public source tree contains only synthetic fixtures and demo data. Never set the cache path to a tracked/public directory when processing private company documents.
