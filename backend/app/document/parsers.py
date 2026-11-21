from pathlib import Path
from decimal import Decimal, InvalidOperation
import re, subprocess, tempfile, zipfile, io, os
import openpyxl
import pdfplumber
from PIL import Image
import pytesseract

def dec(value):
    if value is None: return None
    s=str(value).replace(",","").replace("₹","").strip()
    try: return Decimal(s)
    except (InvalidOperation,ValueError): return None

def parse_excel_boq(path: Path) -> list[dict]:
    wb=openpyxl.load_workbook(path,data_only=True,read_only=True)
    candidates=[]
    for ws in wb.worksheets:
        rows=list(ws.iter_rows(values_only=True))
        for i,row in enumerate(rows[:25]):
            vals=[str(v or "").strip().lower() for v in row]
            desc=next((j for j,v in enumerate(vals) if "description" in v or "particulars" in v),None)
            # Prefer explicit total columns when present; do not treat dimension columns as quantities.
            qty=next((j for j,v in enumerate(vals) if v in {"total (sft)","total (sqft)","total quantity","quantity","qty"} or v.startswith("quantity")),None)
            unit=next((j for j,v in enumerate(vals) if v in {"unit","uom","u.o.m","uom."} or v=="unit of measurement"),None)
            forced_unit=None
            if desc is not None and qty is None:
                qty=next((j for j,v in enumerate(vals) if "total" in v and ("sft" in v or "sqft" in v)),None)
                if qty is not None: forced_unit="SQFT"
            if desc is not None and qty is not None:
                score=(150 if "wo item-wise boq" in ws.title.lower() else 0)+(100 if "boq" in ws.title.lower() else 0)+(30 if unit is not None else 0)+(20 if i<10 else 0)
                candidates.append((score,ws,rows,i,desc,qty,unit,forced_unit))
                break
    if not candidates: return []
    candidates.sort(key=lambda x:x[0],reverse=True)
    _,ws,rows,header_idx,desc_idx,qty_idx,unit_idx,forced_unit=candidates[0]
    results=[]
    for ridx,row in enumerate(rows[header_idx+1:],start=header_idx+2):
        if max(desc_idx,qty_idx)>=len(row): continue
        desc=str(row[desc_idx] or "").strip()
        if not desc or desc.lower() in {"total","grand total"}: continue
        q=dec(row[qty_idx])
        unit=(forced_unit or (str(row[unit_idx] or "").strip() if unit_idx is not None and unit_idx<len(row) else ""))
        if q is not None or len(desc)>5:
            results.append({"description":desc,"quantity":str(q) if q is not None else None,"unit":unit or None,
                            "source":{"document":path.name,"locator":f"{ws.title}!row {ridx}"}})
    return results

def load_erp_catalogue(path: Path) -> list[dict]:
    wb=openpyxl.load_workbook(path,data_only=True,read_only=True)
    for ws in wb.worksheets:
        rows=list(ws.iter_rows(values_only=True))
        header=None
        for i,row in enumerate(rows[:10]):
            vals=[str(v or "").strip().lower() for v in row]
            code=next((j for j,v in enumerate(vals) if "item code" in v or v=="code"),None)
            desc=next((j for j,v in enumerate(vals) if "description" in v),None)
            unit=next((j for j,v in enumerate(vals) if v in {"unit","uom","u.o.m","unit of measurement"}),None)
            if code is not None and desc is not None: header=(i,code,desc,unit); break
        if header:
            i,c,d,u=header; out=[]
            for row in rows[i+1:]:
                if len(row)>max(c,d) and row[c] and row[d]:
                    unit_value=row[u] if u is not None and u<len(row) else None
                    out.append({"code":str(row[c]).strip(),"description":str(row[d]).strip(),
                                "unit":str(unit_value).strip() if unit_value else None})
            return out
    return []


def parse_excel_quotation(path: Path) -> dict:
    """Extract vendor quotation cells without computing or filling missing values."""
    wb=openpyxl.load_workbook(path,data_only=True,read_only=True)
    lines=[]; terms=[]; gst={"basis":"unstated","rate_percent":None,"evidence":[]}
    quote_date=None
    term_keys={"pf_esi_registration":("pf","esi"),"tds":("tds",),
               "security_deposit":("security deposit",),"gst_extra":("gst",),
               "water_electricity_hutment":("water","electricity"),"safety_ppe":("ppe",)}
    other_term_markers=("validity", "delivery", "payment", "warranty", "completion period", "quotation valid")
    for ws in wb.worksheets:
        rows=list(ws.iter_rows(values_only=True))
        header=None
        for i,row in enumerate(rows[:20]):
            vals=[str(v or "").strip().lower() for v in row]
            desc=next((j for j,v in enumerate(vals) if any(k in v for k in ("description","particulars","item description","item name"))),None)
            qty=next((j for j,v in enumerate(vals) if v in {"qty","quantity","quoted qty","quoted quantity"}),None)
            unit=next((j for j,v in enumerate(vals) if v in {"unit","uom","u.o.m","unit of measurement"}),None)
            rate=next((j for j,v in enumerate(vals) if v in {"rate","unit rate","rate per unit","price per unit","basic rate"} or ("rate" in v and "gst" not in v)),None)
            amount=next((j for j,v in enumerate(vals) if v in {"amount","total amount","line total","value","total"} or "amount" in v),None)
            if desc is not None and any(x is not None for x in (qty,unit,rate,amount)):
                header=(i,desc,qty,unit,rate,amount); break
        if header:
            i,d,q,u,r,a=header
            for row_no,row in enumerate(rows[i+1:],start=i+2):
                if d>=len(row) or not row[d]: continue
                description=str(row[d]).strip()
                if description.lower() in {"total","grand total","subtotal"}: continue
                def cell(index): return row[index] if index is not None and index<len(row) else None
                quantity=dec(cell(q)); unit_value=cell(u); rate_value=dec(cell(r)); amount_value=dec(cell(a))
                if quantity is None and unit_value is None and rate_value is None and amount_value is None and any(
                    marker in description.lower() for marker in ("gst", "tds", "pf", "esi", "security deposit", "safety", "ppe", "water", "electricity")
                ):
                    continue
                evidence={"document":path.name,"locator":f"{ws.title}!row {row_no}",
                          "snippet":" | ".join(str(v) for v in row if v is not None)[:350]}
                lines.append({"description":description,"quantity":str(quantity) if quantity is not None else None,
                    "unit":str(unit_value).strip() if unit_value is not None else None,
                    "rate":str(rate_value) if rate_value is not None else None,
                    "amount_stated":str(amount_value) if amount_value is not None else None,"evidence":evidence})
        for row_no,row in enumerate(rows,1):
            for col_no,value in enumerate(row,1):
                text=str(value).strip() if value is not None else ""
                if not text: continue
                lower=text.lower()
                evidence={"document":path.name,"locator":f"{ws.title}!{row_no},{col_no}","snippet":text[:300]}
                if "gst" in lower:
                    if re.search(r"gst\s*(?:extra|additional)|plus\s*gst",lower): gst["basis"]="extra"
                    elif re.search(r"including\s*gst|gst\s*included|inclusive\s*of\s*gst",lower): gst["basis"]="inclusive"
                    rate_match=re.search(r"(\d+(?:\.\d+)?)\s*%",text)
                    if rate_match: gst["rate_percent"]=rate_match.group(1)
                    if not gst["evidence"]: gst["evidence"]=[evidence]
                for key,needles in term_keys.items():
                    if all(n in lower for n in needles) and not any(t["key"]==key for t in terms):
                        terms.append({"key":key,"text":text,"evidence":evidence})
                if any(marker in lower for marker in other_term_markers):
                    terms.append({"key":"other","text":text,"evidence":evidence})
                if quote_date is None:
                    date_match=re.search(r"(?:quotation\s+date|quote\s+date|date)\s*[:\-]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",text,re.I)
                    if date_match:
                        from datetime import datetime
                        for fmt in ("%d.%m.%Y","%d/%m/%Y","%d-%m-%Y","%d.%m.%y","%d/%m/%y"):
                            try: quote_date=datetime.strptime(date_match.group(1),fmt).date().isoformat(); break
                            except ValueError: pass
    return {"quote_date":quote_date,"gst":gst,"lines":lines,"terms":terms}

def pdf_text(path: Path) -> tuple[str,str]:
    pages=[]
    used_ocr=False
    with pdfplumber.open(path) as pdf:
        for i,page in enumerate(pdf.pages,1):
            txt=page.extract_text() or ""
            if len(txt.strip())<100:
                with tempfile.TemporaryDirectory() as td:
                    prefix=str(Path(td)/"page")
                    try:
                        proc=subprocess.run(["pdftoppm","-f",str(i),"-l",str(i),"-png","-r","220",str(path),prefix],
                                            capture_output=True,text=True)
                        imgs=list(Path(td).glob("page-*.png"))
                        if proc.returncode==0 and imgs:
                            txt=pytesseract.image_to_string(Image.open(imgs[0]))
                            used_ocr=True
                    except (OSError, Exception):
                        pass
            pages.append((i,txt))
    method="text_pdf_ocr" if used_ocr and any(len(t.strip())>20 for _,t in pages) else ("text_pdf" if any(len(t.strip())>20 for _,t in pages) else "scanned_pdf_ocr")
    return "\\n".join(f"[PAGE {i}]\\n{t}" for i,t in pages),method

def parse_quote_text(text: str, filename: str) -> dict:
    lines=[]
    page_blocks=list(re.finditer(r"\[PAGE (\d+)\](.*?)(?=\[PAGE \d+\]|$)",text,re.S))
    for page_match in page_blocks:
        page=int(page_match.group(1)); page_text=page_match.group(2)
        for raw in page_text.splitlines():
            normalised_row=re.sub(r"\s*[|]\s*", " ", raw)
            m=re.search(r"(.{5,}?)\s+(SQFT|SQM|SOFT|SFT|SQ\s*FT|M2|M²|RFT|NOS|CUM|KG)\s+([\d,]+(?:\.\d+)?)(?:\s+([\d,]+(?:\.\d+)?))?(?:\s+([\d,]+(?:\.\d+)?))?\s*$",normalised_row,re.I)
            if m:
                lines.append({"description":m.group(1).strip(),"unit":m.group(2).upper(),
                    "quantity":str(dec(m.group(3))),"rate":str(dec(m.group(4))) if m.group(4) else None,
                    "amount_stated":str(dec(m.group(5))) if m.group(5) else None,
                    "evidence":{"document":filename,"page":page,"snippet":raw.strip()[:350]}})
    gst_basis="unstated"
    if re.search(r"GST\s*(?:extra|additional)",text,re.I): gst_basis="extra"
    elif re.search(r"including\s+GST|GST\s+included",text,re.I): gst_basis="inclusive"
    gst_match=re.search(r"GST\s*@?\s*(\d+(?:\.\d+)?)\s*%",text,re.I)
    gst_evidence=[]
    for block in page_blocks:
        for raw in block.group(2).splitlines():
            if "gst" in raw.lower():
                gst_evidence=[{"document":filename,"page":int(block.group(1)),"snippet":raw.strip()[:300]}]
                break
        if gst_evidence: break
    date_match=re.search(r"(?:quotation\s+date|quote\s+date|date)\s*[:\-]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",text,re.I)
    quote_date=None
    if date_match:
        from datetime import datetime
        raw_date=date_match.group(1)
        for fmt in ("%d.%m.%Y","%d/%m/%Y","%d-%m-%Y","%d.%m.%y","%d/%m/%y"):
            try:
                quote_date=datetime.strptime(raw_date,fmt).date().isoformat()
                break
            except ValueError:
                pass
    term_keys={"pf_esi_registration":("pf","esi"),"tds":("tds",),"security_deposit":("security deposit",),
               "gst_extra":("gst",),"water_electricity_hutment":("water","electricity"),
               "safety_ppe":("ppe",)}
    other_term_markers=("validity", "delivery", "payment", "warranty", "completion period", "quotation valid")
    terms=[]
    for key,needles in term_keys.items():
        for block in page_blocks:
            page=int(block.group(1))
            for raw in block.group(2).splitlines():
                if all(n in raw.lower() for n in needles):
                    terms.append({"key":key,"text":raw.strip(),"evidence":{"document":filename,"page":page,"snippet":raw.strip()[:300]}})
                    break
            if any(t["key"]==key for t in terms): break
    for block in page_blocks:
        page=int(block.group(1))
        for raw in block.group(2).splitlines():
            if any(marker in raw.lower() for marker in other_term_markers):
                terms.append({"key":"other","text":raw.strip(),"evidence":{"document":filename,"page":page,"snippet":raw.strip()[:300]}})
    return {"vendor_name":None,"quote_date":quote_date,
            "gst":{"basis":gst_basis,"rate_percent":gst_match.group(1) if gst_match else None,"evidence":gst_evidence},
            "lines":lines,"terms":terms}

def pdf_sparse_pages(path: Path, threshold: int = 100) -> list[int]:
    with pdfplumber.open(path) as pdf:
        return [i for i,page in enumerate(pdf.pages,1) if len((page.extract_text() or "").strip()) < threshold]

def render_pdf_pages(path: Path, max_pages: int = 8, selected_pages: list[int] | None = None) -> list[tuple[int,bytes]]:
    rendered=[]
    with tempfile.TemporaryDirectory() as td:
        pages=selected_pages or list(range(1,max_pages+1))
        for page_no in pages:
            prefix=str(Path(td)/f"page{page_no}")
            subprocess.run(["pdftoppm","-png","-r","180","-f",str(page_no),"-l",str(page_no),str(path),prefix],
                           capture_output=True,text=True)
            imgs=list(Path(td).glob(f"page{page_no}-*.png"))
            if imgs: rendered.append((page_no,imgs[0].read_bytes()))
    return rendered
