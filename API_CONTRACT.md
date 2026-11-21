# API CONTRACT

Source of truth in code: `backend/app/schemas/*.py` (Pydantic). **Canonical example payloads:** `frontend/src/mocks/*.json`
(synthetic; validated against the schemas by `tests/test_frontend_mocks.py`). If this document and the schemas disagree, the schemas win; tell Member 3.

Base path `/api`. JSON in/out except uploads (`multipart/form-data`). No authentication (out of scope).

## Conventions

- **Decimals** (money, quantities, rates): JSON **strings**, e.g. `"1200.50"`. Input may be string or number; never floats in logic.
- **Dates:** ISO `YYYY-MM-DD`. **Timestamps:** ISO-8601 UTC.
- **Unknown fields are rejected** (422). **Null means UNKNOWN** (never a guess).
- **Evidence:** `SourceEvidence {document, page?, locator?, snippet?}` accompanies every extracted/derived value.
- **Flag:** `{code, severity: info|warning|blocking, message, evidence[]}`. Codes: `QTY_MISMATCH, UNIT_MISMATCH, UNIT_UNKNOWN, MISSING_RATE,
  ITEM_NOT_QUOTED, EXTRA_ITEM_QUOTED, GST_UNSTATED, TERM_DEVIATION, TERM_NOT_STATED, ARITHMETIC_MISMATCH, LOW_OCR_CONFIDENCE,
  LOW_MATCH_CONFIDENCE, NEAR_DUPLICATE_CODE, UNRESOLVED_REVIEW`.
- **AITrace:** `{step, provider, model?, attempt, status: ok|repaired|fallback|cached|failed, latency_ms?, error?}`. Any endpoint that used AI returns `ai_trace[]`.
- **Six terms** (`TermKey`): `pf_esi_registration, tds, security_deposit, gst_extra, water_electricity_hutment, safety_ppe`.

## Error format (all non-2xx)

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Request validation failed",
             "details": [{"loc": "body.quotation_ids", "msg": "..."}], "request_id": "a1b2c3d4e5f6" } }
```

| HTTP | `code` | When |
|---|---|---|
| 404 | `NOT_FOUND` | Unknown route or id |
| 405 | `METHOD_NOT_ALLOWED` | Wrong verb |
| 409 | `CONFLICT_STATE` | e.g. approving a comparison that already has an approval; shortlist before comparison exists |
| 413 | `FILE_TOO_LARGE` | Upload > `MAX_UPLOAD_MB` |
| 415 | `UNSUPPORTED_FILE_TYPE` | Not `.xlsx`, `.pdf`, `.png`, `.jpg` |
| 422 | `VALIDATION_ERROR` | Schema/field validation failed |
| 422 | `EXTRACTION_FAILED` | File unreadable / nothing extractable |
| 501 | `NOT_IMPLEMENTED` | Endpoint contract exists, logic not built yet |
| 502 | `AI_PROVIDER_UNAVAILABLE` | All providers failed/timeouts and no cached sample |
| 502 | `AI_OUTPUT_INVALID` | Output invalid after the one repair attempt |
| 500 | `INTERNAL_ERROR` | Unexpected |

## Endpoints

Status today: only `GET /api/health` is functional. The other seven enforce the request contract and return `501`.

### GET `/api/health`
Response 200: `{status: "ok"|"degraded", version, database: "ok"|"error", ai: {primary_configured, fallback_configured, cached_samples_enabled}}`.
Never returns key values. Errors: none expected.

### POST `/api/requirements/intake`  (multipart)
| Field | Type | Rules |
|---|---|---|
| `email_text` | string, required | non-empty |
| `boq_file` | file, optional | `.xlsx` only |
| `note_text` | string, optional | free text, Hindi/Bengali/English |
| `note_language` | `en`\|`hi`\|`bn`, optional | |

Response 200 `IntakeResponse`: `requirement_id, project_name?, scope_summary?, items[{line_no, description, quantity?{value,unit}, source, flags[]}], note?{language, original_text, english_summary?, ai_generated}, warnings[], ai_trace[]`.
Rules: quantities come from BOQ cells (deterministic). Without a BOQ, `quantity` is null (UNKNOWN). Errors: 415, 413, 422, 502.

### POST `/api/requirements/match`  (JSON)
Request `{requirement_id, line_nos?: int[]}` (null = all lines).
Response 200 `MatchResponse`: `requirement_id, matches[{line_no, status: matched|ambiguous|unmatched, suggestions[<=5]{item_code, description, erp_unit?, confidence 0..1, rationale, near_duplicates[{item_code, description, similarity}]}, flags[]}], ai_trace[]`.
Rules: codes only from the ERP catalogue; near-duplicates always surfaced; confidence calibration is an **ASSUMPTION**. Errors: 404 (requirement), 422, 502.

### POST `/api/rfq/generate`  (JSON)
Request `{requirement_id, confirmed_items: [{line_no, item_code}] (min 1), response_due_date?, terms_override?: CommercialTerm[6]}`.
`terms_override`, if given, must contain each of the six `TermKey`s exactly once.
Response 200 `RfqResponse`: `rfq_id, requirement_id, subject, body_text, items[{line_no, item_code, description, quantity}], terms[6]{key,text}, response_due_date?`.
Errors: 404, 409 (line not matched/confirmed), 422.

### POST `/api/quotations/upload`  (multipart; one call per vendor file)
Fields: `rfq_id` (required), `vendor_name` (required, typed by the user; never inferred silently), `file` (required: `.pdf`, `.xlsx`, `.png`, `.jpg`).
Response 200 `QuotationResponse`: `quotation_id, rfq_id, vendor_name, source_file, extraction_method: excel|text_pdf|scanned_pdf_ocr|image_ocr|cached_sample, quote_date?, validity_text?, gst{basis: extra|inclusive|unstated, rate_percent?, evidence?}, lines[{line_no?, description, quantity?, rate?, rate_unit?, amount_stated?, evidence}], terms[{key|"other", text, evidence}], extraction_confidence?, warnings[], ai_trace[]`.
Rules: values are as written by the vendor; nothing normalised or recomputed here; low OCR confidence -> `LOW_OCR_CONFIDENCE` flag. Errors: 404 (rfq), 413, 415, 422 (`EXTRACTION_FAILED`), 502.

### POST `/api/comparisons/generate`  (JSON)
Request `{rfq_id, quotation_ids: string[2..6], resolutions?: [{quotation_id, rfq_line_no, factor>0, note, resolved_by}]}`.
Response 200 `ComparisonResponse`: `comparison_id, rfq_id, created_at, computed_by:"deterministic", standard_terms[6], rows[{rfq_line_no, item_code, description, rfq_quantity, cells[{quotation_id, vendor_name, status: comparable|needs_review|not_quoted, quoted_quantity?, rate?, amount_at_rfq_qty?, amount_stated_by_vendor?, flags[], evidence[]}]}], vendors[{quotation_id, vendor_name, subtotal_comparable?, gst_basis, gst_rate_percent?, gst_amount?, total_incl_gst?, lines_comparable, lines_needs_review, lines_not_quoted, term_deviations[{key, status: accepted|deviation|not_stated, standard_text, vendor_text?, evidence?}], flags[]}], flags[]`.
Rules (deterministic, no AI):
- `amount_at_rfq_qty = rfq_quantity x rate` and only when `status == comparable`; otherwise null.
- Unit or quantity differs from the RFQ -> `needs_review` + `UNIT_MISMATCH`/`QTY_MISMATCH` (blocking). Only a matching `resolutions` entry changes that; the resolution is echoed in evidence.
- `gst_basis == unstated` -> `total_incl_gst = null`, `GST_UNSTATED`.
- Vendor's stated amount != recomputed -> `ARITHMETIC_MISMATCH`.
- Calling again with `resolutions` produces a **new** `comparison_id` (comparisons are immutable).
Errors: 404, 409 (quotation belongs to a different RFQ), 422.

### POST `/api/comparisons/{comparison_id}/shortlist`  (JSON; body optional)
Request `{rules?: {max_vendors 1..4 (default 3), exclude_on_blocking_flags (default true), exclude_if_term_rejected: TermKey[] (default [])}}`.
Response 200 `ShortlistResponse`: `comparison_id, rules_applied, shortlist[{rank, quotation_id, vendor_name, total_incl_gst, reasons[{text, evidence[]}], caveats[]}], pending_review[{quotation_id, vendor_name, reasons[]}], excluded[...], decision_support_only: true`.
Rules: only vendors with all lines comparable and a known total are ranked, ascending by `total_incl_gst`. Others go to `pending_review` or `excluded` with reasons. Reasons are template text over stored facts. Errors: 404, 422.

### POST `/api/approvals/{comparison_id}`  (JSON)
Request `{decision: approve|override|reject_all, selected_quotation_id?, approver_name (required, free text), note?, override_reason?}`.
Validation: `approve`/`override` require `selected_quotation_id`; `reject_all` forbids it; `override` requires `override_reason`.
Server checks: `approve` requires the vendor to be in the stored shortlist (else 422); `override` allows any quoted vendor.
Response 200 `ApprovalResponse`: `approval_id, comparison_id, decision, selected_quotation_id?, vendor_name?, is_override, approval_note, approver_name, decided_at`.
`approval_note` is generated from a template over stored facts (totals, rank, flags, override reason): not LLM text. Errors: 404, 409 (already decided), 422.

## Typical call sequence

`intake -> match -> (human confirms codes) -> rfq/generate -> quotations/upload x4 -> comparisons/generate -> (human resolves mismatches, re-generate) -> shortlist -> approvals`
