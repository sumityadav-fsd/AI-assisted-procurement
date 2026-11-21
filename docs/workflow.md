# Procurement workflow (as the product models it)

Owner: Member 3. Derived from the problem statement. **UNKNOWN:** Vinayak's real 12-step SOP detail has not been mapped here yet
(Member 3: summarise it in your own words, without copying real data, once read).

## Today (manual) vs with ProcureAI

| # | Stage | Who | ProcureAI support |
|---|---|---|---|
| 1 | Site sends requirement (email, BOQ sheet, sometimes WhatsApp/voice note) | Site engineer | **Intake**: structure email + BOQ + optional Hindi/Bengali note |
| 2 | Contracts team maps lines to ERP item codes | Contracts & Planning | **Match**: suggestions, confidence, near-duplicate warnings; human confirms |
| 3 | RFQ drafted and emailed to vendors with six standard terms | Contracts & Planning | **RFQ generator** (text for the user to send; we do not send email) |
| 4 | Vendors reply with quotations in their own formats (one may be a scan) | Vendors | **Quotation intelligence**: extract lines, rates, GST, terms, with evidence |
| 5 | Comparative statement built by hand | Contracts & Planning | **Comparison**: normalised, deterministic, flagged |
| 6 | Management reviews, negotiates, approves rates | Management | **Decision**: rule-based shortlist, evidence, human approval/override |
| 7+ | Work order, vendor onboarding, etc. | | **Out of scope** |

## Human-in-the-loop checkpoints

1. After matching: human confirms/changes every ERP code before an RFQ is generated.
2. After comparison: human resolves each unit/quantity mismatch (supplies a conversion factor) or leaves the vendor in `pending_review`.
3. At the end: human approves, overrides (reason mandatory) or rejects all. The system never selects a vendor.

## Standard commercial terms (six, keyed)

`pf_esi_registration`, `tds`, `security_deposit`, `gst_extra`, `water_electricity_hutment`, `safety_ppe`.
Wording and parameters (e.g. deposit %, release period) live in a synthetic config/fixture, not in code.
**UNKNOWN:** whether the parameters vary per project (see mentor questions).

## Failure handling the demo must show

- AI provider times out -> fallback provider -> cached sample; each shown in the AI trace panel.
- Scanned quotation with weak OCR -> `LOW_OCR_CONFIDENCE`, values shown with evidence, never silently trusted.
- Vendor quotes a different quantity or unit -> flagged, excluded from totals until a human resolves.
- GST not stated -> total shown as UNKNOWN, not guessed.
