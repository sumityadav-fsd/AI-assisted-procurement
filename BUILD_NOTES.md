# Vinayak ProcureAI — implementation notes

- Removed the synthetic demo endpoint from the user-facing application. The `/api/demo/load` route is no longer exposed.
- The Amara import now uses the actual supplied site email and BOQ workbook.
- ERP candidate ranking is Sarvam semantic matching over the actual ERP workbook. Returned item codes are allow-listed against that workbook; authoritative descriptions and units are rehydrated from the workbook. Human confirmation is still mandatory.
- RFQ drafting now calls Sarvam using only human-confirmed items and the six company terms. A validation guard falls back to a deterministic exact-fact RFQ if the model omits any controlled item/code/term.
- Requirement email interpretation and quotation extraction already use Sarvam chat; scanned PDFs use Sarvam Document AI when configured.
- Cached model responses are disabled by default and cannot be used as a silent substitute for live AI. AI traces show Sarvam success/retry/failure and deterministic fallback.
- Comparison arithmetic remains deterministic Decimal arithmetic. Shortlist eligibility remains rule-based and human approval remains explicit.
- No live Sarvam call was possible in this build environment because the user's API key is not available here. Configure `SARVAM_API_KEY` in `.env` and verify `/api/health` before demo/deployment.
- Private Vinayak source documents remain in `data_private/`; the pack's own README prohibits sharing outside the hackathon team and portfolio/public use without permission. Do not deploy this bundled-data ZIP publicly.
