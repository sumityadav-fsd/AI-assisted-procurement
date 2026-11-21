"""Document extraction (PDF / Excel / OCR) -> raw structured text and tables. OWNER: Member 3.

RULES
- Deterministic code only. MUST NOT import app.ai (enforced by tests/test_architecture_rules.py).
- Every extracted value carries a SourceEvidence (document, page, locator, snippet).
- Report extraction method and confidence honestly; never "fix" numbers.
- Interfaces to implement are in ./interfaces.py.
"""
