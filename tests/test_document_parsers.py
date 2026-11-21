from pathlib import Path

import openpyxl

from app.document.parsers import load_erp_catalogue, parse_excel_quotation


def test_excel_quotation_extracts_cells_and_source_evidence(tmp_path):
    path = tmp_path / "synthetic_quotation.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Synthetic Quote"
    ws.append(["Item Description", "Quantity", "Unit", "Rate", "Amount"])
    ws.append(["Synthetic cement work", 12, "BAG", 250.5, 3006])
    ws.append(["GST extra @ 18%"])
    ws.append(["TDS as applicable"])
    wb.save(path)

    parsed = parse_excel_quotation(path)
    assert len(parsed["lines"]) == 1
    line = parsed["lines"][0]
    assert line["quantity"] == "12"
    assert line["unit"] == "BAG"
    assert line["rate"] == "250.5"
    assert line["amount_stated"] == "3006"
    assert line["evidence"]["locator"] == "Synthetic Quote!row 2"
    assert parsed["gst"]["basis"] == "extra"
    assert parsed["gst"]["rate_percent"] == "18"
    assert {term["key"] for term in parsed["terms"]} >= {"tds", "gst_extra"}


def test_erp_catalogue_extracts_code_description_and_unit(tmp_path):
    path = tmp_path / "synthetic_erp.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Item Code", "Description", "Unit"])
    ws.append(["SYN-001", "Synthetic item", "NOS"])
    wb.save(path)
    assert load_erp_catalogue(path) == [{"code": "SYN-001", "description": "Synthetic item", "unit": "NOS"}]


def test_pdf_text_parser_preserves_page_evidence_and_extra_terms():
    from app.document.parsers import parse_quote_text
    parsed = parse_quote_text(
        "[PAGE 1]\nSynthetic waterproofing | SQFT | 5 | 10 | 50\nGST extra @ 18%\nPayment within 30 days",
        "synthetic_quote.pdf",
    )
    assert parsed["lines"][0]["quantity"] == "5"
    assert parsed["lines"][0]["rate"] == "10"
    assert parsed["lines"][0]["amount_stated"] == "50"
    assert parsed["lines"][0]["evidence"]["page"] == 1
    assert parsed["gst"]["basis"] == "extra"
    assert any(term["key"] == "other" for term in parsed["terms"])
