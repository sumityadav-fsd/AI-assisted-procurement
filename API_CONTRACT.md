# API CONTRACT — Vinayak ProcureAI local MVP

Base path `/api`. JSON in/out except multipart uploads. All money, rates and quantities are represented as decimal strings in stored/output data. No authentication.

## Conventions
- Unknown values are `null` / `UNKNOWN`; never infer them.
- Evidence: `{document, page?, locator?, snippet?}`.
- Flags: `{code, severity: info|warning|blocking, message, evidence[]}`.
- AITrace: `{step, provider, model?, attempt, status: ok|repaired|fallback|cached|failed, latency_ms?, error?}`.
- Six term keys: `pf_esi_registration, tds, security_deposit, gst_extra, water_electricity_hutment, safety_ppe`.
- Error envelope: `{ "error": { "code", "message", "details": [], "request_id" } }`.

## Endpoints

### GET `/api/health`
Returns `{status, version, database, ai:{primary_configured, fallback_configured, cached_samples_enabled}}`. Never returns secret values.

### POST `/api/requirements/intake` (multipart)
Fields: `email_text` required; `boq_file` optional `.xlsx`; `note_text` optional; `note_language` optional `en|hi|bn`.
Returns `IntakeResponse`: `requirement_id, project_name?, scope_summary?, items[{line_no, description, quantity?{value,unit}, source, flags[]}], note?, warnings[], ai_trace[]`.
BOQ quantities are extracted from workbook cells only. Email-only quantity is UNKNOWN. Sarvam may structure project/scope text or summarise Hindi/Bengali notes, never quantities.

### POST `/api/requirements/match` (JSON)
Request `{requirement_id, line_nos?: int[]}`.
Returns `MatchResponse`: `requirement_id, matches[{line_no, status, suggestions[{item_code,description,erp_unit?,confidence,rationale,near_duplicates[]}], confirmed_code?, flags[]}], ai_trace[]`.
Candidates are deterministic lexical matches from the workbook at `ERP_CATALOGUE_PATH` (default: private data-pack ERP workbook). Codes are never invented. Human must select a returned candidate.

### POST `/api/rfq/generate` (JSON)
Request `{requirement_id, confirmed_items:[{line_no>0,item_code}], response_due_date?, terms_override?:[{key,text} x 6]}`. Nested confirmed item objects reject unknown fields.
If `terms_override` is supplied it must contain all six term keys exactly once.
Returns `{rfq_id, requirement_id, subject, body_text, items[], terms[6], response_due_date?}`.
Default wording is read at runtime from the private RFQ sample. Missing terms remain UNKNOWN.

### POST `/api/quotations/upload` (multipart; one vendor file per call)
Fields: `rfq_id`, `vendor_name` (typed by user), `file` (`.pdf`, `.xlsx`, `.png`, `.jpg`, `.jpeg`).
Returns `QuotationResponse`: `quotation_id, rfq_id, vendor_name, source_file, extraction_method, quote_date?, validity_text?, gst{basis,rate_percent?,evidence[]}, lines[{description,quantity?,unit?,rate?,amount_stated?,evidence,rfq_line_no?,match_confidence?,match_status?}], terms[], term_deviations[], extraction_confidence?, warnings[], ai_trace[]`.
Digital PDF/Excel parsing is deterministic. Sparse/scanned PDF and image inputs use Sarvam Document AI Parse when configured (multipart `POST /doc-ai/v1/job/parse`, poll `GET /doc-ai/v1/job/{job_id}/status`, then `GET /doc-ai/v1/job/{job_id}/download-url` and download the ZIP). If Sarvam is unavailable, local Tesseract/Poppler is attempted. Sarvam text structuring may organise extracted values but cannot calculate, normalise or infer them. Missing fields stay null.

### POST `/api/comparisons/generate` (JSON)
Request `{rfq_id, quotation_ids:[2..6], resolutions?:[{quotation_id,rfq_line_no,factor>0,note,resolved_by}]}`.
Returns `ComparisonResponse`: `comparison_id, rfq_id, created_at, computed_by:"deterministic", standard_terms[6], rows[{rfq_line_no,item_code,description,rfq_quantity,cells[]}], vendors[], flags[]`.
Rules:
- All arithmetic uses Python Decimal.
- `amount_at_rfq_qty = rfq_quantity × comparable_rate`; null unless the line is comparable.
- Unit, quantity or uncertain line mapping requires human UnitResolution. Unresolved lines are blocking and excluded from totals.
- `factor` means quoted-units per RFQ-unit. The rate is divided by factor when converting a quoted unit to the RFQ unit.
- Quoted quantity × quoted rate is checked against vendor stated amount; mismatch => `ARITHMETIC_MISMATCH`.
- Missing/unstated GST basis or missing GST rate when GST is extra => `total_incl_gst = null`.
- Any unresolved or unquoted RFQ line prevents a vendor subtotal/total from being presented as fully comparable.
- Re-running with resolutions creates a new immutable comparison ID.

### POST `/api/comparisons/{comparison_id}/shortlist` (JSON; body optional)
Request `{rules?:{max_vendors:1..4,exclude_on_blocking_flags:boolean,exclude_if_term_rejected:TermKey[]}}`.
Returns `{comparison_id,rules_applied,shortlist[{rank,quotation_id,vendor_name,total_incl_gst,reasons[{text,evidence[]}],caveats[]}],pending_review[],excluded[],decision_support_only:true}`.
Only fully comparable vendors with known GST-inclusive totals are ranked, ascending by total. No historical performance or invented ratings.

### POST `/api/approvals/{comparison_id}` (JSON)
Request `{decision:approve|override|reject_all,selected_quotation_id?,approver_name,note?,override_reason?}`.
Approve/override require selected quotation; reject_all forbids one; override requires reason. Approve requires a stored shortlist entry; override may select any quotation. One decision per comparison.
Returns `{approval_id,comparison_id,decision,selected_quotation_id?,vendor_name?,is_override,approval_note,approver_name,decided_at}`. The note is template text over stored facts, not LLM-generated.

### POST `/api/demo/load`
Loads an entirely synthetic offline demo: requirement, candidate codes, RFQ, four sample quotations (including a synthetic scanned-OCR case), comparison and shortlist. No internet or Sarvam key required. Never uses real company data.

## Error codes
`NOT_FOUND`, `CONFLICT_STATE`, `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE`, `VALIDATION_ERROR`, `MATCH_CONFIRMATION_REQUIRED`, `OVERRIDE_REASON_REQUIRED`, `INTERNAL_ERROR`.
