# Mentor questions and unresolved assumptions

Owner: Member 3. Mark answers here with date/time and who answered.

## Ask first (blocks design)

1. **Real data and external AI:** may Vinayak's real documents be sent to Sarvam AI / a fallback provider during the hackathon? Which providers are acceptable?
   Until answered, build and demo on synthetic data; keep any real-data caches in gitignored `data_private/`.
2. **Comparison basis:** compare vendors at the **RFQ quantity** (our ASSUMPTION) or at each vendor's own quoted quantity? Quotes in the data pack differ in quantities and dates.
3. **Unit/quantity mismatch policy:** is flag-and-exclude-until-human-resolves correct, or should some conversions (e.g. sqft to sqm) be auto-applied with a visible note?
4. **GST:** if a vendor does not state GST basis, is "total unknown" right, or does Vinayak assume the RFQ term (GST extra)?

## Assumptions we made (ASSUMPTION)

- Shortlist = lowest total incl. GST among vendors whose lines are all comparable; term deviations shown as caveats, not auto-penalised.
- Approval has no authentication; `approver_name` is free text.
- Near-duplicate ERP descriptions are surfaced to the human, never auto-resolved.
- Confidence scores for ERP matching are heuristic, not calibrated.
- RFQ is generated as text for a human to send; the system sends no email.
- Standard six terms are the same for every RFQ.

## Unknowns (UNKNOWN)

- Sarvam AI's API surface (endpoint, auth, JSON mode, context limits, Hindi/Bengali handling, vision/OCR support).
- Which fallback provider to use, and its API.
- OCR approach for the scanned quotation: Tesseract (needs system package, `hin`/`ben` data) vs provider vision.
- How requirements arriving by WhatsApp/voice should be represented (the data pack has none; we make synthetic samples).
- Whether term parameters (deposit %, retention period) vary by project.
- Expected quotation count per RFQ beyond four, and whether partial-item quotes are normal.
- How management wants vendor performance captured later (out of scope now; we show no ratings).
- Whether the deployed demo URL may hold any real data (we assume not).
