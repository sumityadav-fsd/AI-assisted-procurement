# Procurement workflow — MVP

This is a product-level summary. It does not reproduce any company-specific source documents or terms.

| Stage | Input | ProcureAI support | Human checkpoint |
|---|---|---|---|
| 1. Requirement intake | Requirement email, Excel BOQ, optional Hindi/Bengali note | Structure project/scope; read BOQ cells deterministically | Review missing or ambiguous lines |
| 2. ERP matching | Requirement lines and private ERP workbook | Deterministic lexical candidates, confidence and near-duplicate warnings | Confirm each ERP code |
| 3. RFQ | Confirmed codes, quantities and six runtime terms | Generate copyable RFQ text | Review and send RFQ outside the app |
| 4. Quotations | Vendor PDF, Excel or image files | Extract lines, rates, quantities, GST and terms with evidence | Review OCR/extraction and line mapping |
| 5. Comparison | RFQ plus 2–6 quotations | Decimal calculations, GST, term differences and flags | Supply UnitResolution for quantity/unit mismatch |
| 6. Decision | Comparative statement and shortlist | Rule-based shortlist, reasons and evidence | Approve, override with reason, or reject all |

## Safety checkpoints

- LLM output never supplies BOQ quantities, ERP item codes, rates, calculated totals or approval decisions.
- ERP candidates are generated deterministically from the configured catalogue; only returned codes can be selected.
- A mismatch or unknown unit blocks comparison totals until a human resolves it.
- Unknown GST basis/rate means the GST-inclusive total is UNKNOWN.
- The app never emails vendors, creates work orders or autonomously selects a vendor.

## AI failure sequence

Sarvam is the only configured provider. For structured output the gateway allows one repair/retry. If that fails, it uses deterministic parsing where available, then an explicitly configured cache under `AI_SAMPLES_DIR`. The default cache directory is gitignored `data_private/ai_samples`. The offline demo uses synthetic data and does not call the provider.
