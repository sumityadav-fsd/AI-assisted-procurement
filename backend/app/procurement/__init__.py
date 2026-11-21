"""Deterministic procurement logic: ERP candidates, normalisation, comparison, shortlist. OWNER: Member 3.

RULES
- Pure functions over Pydantic models and Decimal. MUST NOT import app.ai or app.document.
- No floats for money or quantity. No rounding until display.
- Never resolve a quantity/unit mismatch on its own: emit a Flag and status 'needs_review'.
  Only a human-supplied UnitResolution may make such a line comparable.
- Interfaces to implement are in ./interfaces.py.
"""
