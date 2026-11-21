# Test cases

End-to-end scenario definitions (synthetic) that Member 3 builds as the deterministic engine lands.
Each case = input JSON (RFQ + extracted quotations) -> expected ComparisonResponse flags.

Must-have scenarios (not written yet):
1. Same unit, same quantity, all four vendors comparable.
2. Vendor quotes different quantity -> QTY_MISMATCH, status needs_review, excluded from totals.
3. Vendor quotes different unit (e.g. sqft vs sqm) -> UNIT_MISMATCH; only a UnitResolution makes it comparable.
4. GST unstated -> total_incl_gst is null (UNKNOWN), vendor listed under pending_review.
5. Vendor total arithmetic disagrees with rate x quantity -> ARITHMETIC_MISMATCH.
6. Term deviation / term not stated.
