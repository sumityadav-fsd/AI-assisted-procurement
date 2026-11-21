# Mentor questions and assumptions

Answers should be recorded with date/time and the person who confirmed them. Do not place real vendor names, rates or source terms in this public document.

## Questions requiring confirmation

1. **External AI permission:** may real company documents be sent to Sarvam Document AI / Sarvam chat during the hackathon? Until confirmed, do not upload private documents to an external provider.
2. **Comparison basis:** confirm that all vendors should be compared at the RFQ quantity (the current implementation assumption).
3. **Mismatch policy:** confirm that quantity/unit differences remain excluded until a named human supplies a `UnitResolution`.
4. **GST:** confirm that an unstated GST basis or missing extra-GST rate must leave the inclusive total UNKNOWN.
5. **Term handling:** confirm whether commercial-term deviations are warnings/caveats only or should block shortlisting.

## Explicit assumptions

- ERP confidence is a deterministic lexical similarity score, not a calibrated probability.
- Similarity threshold for classifying a vendor term as accepted is an ASSUMPTION and needs mentor review.
- Shortlist ranks only vendors with all RFQ lines comparable and a known GST-inclusive total.
- No vendor ratings or historical performance are available; none are invented.
- Approval identity is free text because authentication is out of scope.

## Known unknowns

- Sarvam live API behaviour and quota under the user's account are UNKNOWN until tested with `SARVAM_API_KEY`.
- OCR accuracy on the private scanned quotation is UNKNOWN until a permitted real-data run and human verification.
- Render persistent storage configuration is deployment-specific and has not been verified here.
