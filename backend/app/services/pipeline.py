from pathlib import Path
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
import re, json, os
from app.core.config import data_pack_dir, erp_catalogue_path, upload_dir, AI_USE_CACHED_SAMPLES, APP_VERSION, SARVAM_API_KEY
from app.database.store import save, get, list_kind, connect
from app.document.parsers import parse_excel_boq, parse_excel_quotation, load_erp_catalogue, pdf_text, parse_quote_text, pdf_sparse_pages
from app.procurement.matching import lexical_candidates
from app.procurement.comparison import build_comparison
from app.schemas.models import IntakeResponse, AITrace, AIQuoteExtraction, IntakeAIOutput
from app.ai.providers import SarvamProvider
from app.ai.gateway import AIGateway

TERMS_KEYS=["pf_esi_registration","tds","security_deposit","gst_extra","water_electricity_hutment","safety_ppe"]

def _id(prefix): return prefix+"_"+uuid4().hex[:12]

def _runtime_terms():
    p=data_pack_dir()/"03_tender"/"Sample_RFQ_email_to_a_vendor.txt"
    if not p.exists():
        return [{"key":k,"text":f"UNKNOWN: standard term {i+1} must be loaded from the private RFQ data pack."} for i,k in enumerate(TERMS_KEYS)]
    lines=[x.strip(" \\t-*•") for x in p.read_text(encoding="utf-8",errors="ignore").splitlines() if x.strip()]
    needles={
        "pf_esi_registration":("pf","esi"),
        "tds":("tds",),
        "security_deposit":("security deposit",),
        "gst_extra":("gst",),
        "water_electricity_hutment":("water","electricity"),
        "safety_ppe":("ppe",)
    }
    terms=[]
    for key in TERMS_KEYS:
        found=next((line for line in lines if all(n in line.lower() for n in needles[key])),None)
        terms.append({"key":key,"text":found or f"UNKNOWN: {key} wording not found in private RFQ sample."})
    return terms

def _email_summary(text):
    project=None
    m=re.search(r"(?:project|site)\s*[:\-]\s*([^\n,]+)",text,re.I)
    if m: project=m.group(1).strip()[:120]
    return project, " ".join(text.split())[:900]

async def intake(email_text, boq_path=None, note_text=None, note_language=None, ai_trace=None):
    req_id=_id("req")
    project,summary=_email_summary(email_text)
    traces=[]
    provider=SarvamProvider()
    schema={"type":"object","properties":{"project_name":{"type":"string"},"scope_summary":{"type":"string"}},
            "required":["project_name","scope_summary"],"additionalProperties":False}
    gateway=AIGateway(provider)
    prompt=("Extract only project name and concise scope summary from this procurement email. "
            "Do not extract or infer any BOQ quantities. Return the requested JSON.\\n\\n"+email_text)
    structured,ai_traces=await gateway.structured(
        "intake_structuring",prompt,schema,
        lambda x: IntakeAIOutput.model_validate(x).model_dump(),
        lambda: {"project_name":project or "","scope_summary":summary or ""})
    project=structured.get("project_name") or project
    summary=structured.get("scope_summary") or summary
    traces=[x.model_dump() for x in ai_traces]
    items=[]
    if boq_path:
        parsed=parse_excel_boq(Path(boq_path))
        for i,row in enumerate(parsed,1):
            items.append({"line_no":i,"description":row["description"],
                "quantity":{"value":row["quantity"],"unit":row["unit"]} if row["quantity"] and row["unit"] else None,
                "source":row["source"],"flags":[]})
    if not items:
        items=[{"line_no":1,"description":summary or "Requirement details require review","quantity":None,
                "source":{"document":"email_text","locator":"submitted text"},"flags":[]}]
    note={"language":note_language or "unknown","original_text":note_text,"english_summary":None,"ai_generated":False} if note_text else None
    if note and note_language in {"hi","bn"}:
        prompt=f"Summarise this procurement note in English. Preserve quantities, units, dates and names exactly. Do not infer missing facts. Source language: {note_language}.\\n\\n{note_text}"
        translated,note_traces=await gateway.text("note_translation",prompt,deterministic_text=None)
        if translated:
            note["english_summary"]=translated
            note["ai_generated"]=True
        else:
            note["warning"]="Translation unavailable; original note retained."
        traces.extend(x.model_dump() for x in note_traces)
    result={"requirement_id":req_id,"project_name":project,"scope_summary":summary,"items":items,"note":note,
            "warnings":[],"ai_trace":traces or [AITrace(step="intake",provider="deterministic",status="fallback").model_dump()]}
    save("requirement",req_id,result)
    return result

def match_requirement(requirement_id, line_nos=None):
    req=get("requirement",requirement_id)
    if not req: return None
    erp_path=erp_catalogue_path()
    catalogue=load_erp_catalogue(erp_path) if erp_path.exists() else []
    # Optional uploaded ERP catalogue supersedes the default runtime catalogue.
    custom=upload_dir()/"erp_catalogue.xlsx"
    if custom.exists(): catalogue=load_erp_catalogue(custom)
    out=[]
    for item in req["items"]:
        if line_nos and item["line_no"] not in line_nos: continue
        suggestions=lexical_candidates(item["description"],catalogue)
        status="unmatched" if not suggestions else ("matched" if suggestions[0]["confidence"]>=0.62 else "ambiguous")
        flags=[]
        if len(suggestions)>1 and suggestions[1]["confidence"]>=0.78:
            flags.append({"code":"NEAR_DUPLICATE_CODE","severity":"warning","message":"Several ERP descriptions are close; human confirmation required.","evidence":[]})
        out.append({"line_no":item["line_no"],"status":status,"suggestions":suggestions,"confirmed_code":None,"flags":flags})
    response={"requirement_id":requirement_id,"matches":out,"ai_trace":[{"step":"erp_match","provider":"deterministic-lexical","status":"fallback","attempt":1}]}
    save("matches",requirement_id,response); return response

def generate_rfq(body):
    req=get("requirement",body.requirement_id)
    if not req: return None
    matches=get("matches",body.requirement_id) or {"matches":[]}
    confirmed={int(x.line_no):x.item_code for x in body.confirmed_items}
    items=[]
    for item in req["items"]:
        if item["line_no"] not in confirmed: continue
        matchrow=next((m for m in matches["matches"] if m["line_no"]==item["line_no"]),None)
        allowed={x["item_code"] for x in matchrow["suggestions"]} if matchrow else set()
        # Codes can only be confirmed from the candidate list.
        if confirmed[item["line_no"]] not in allowed: continue
        items.append({"line_no":item["line_no"],"item_code":confirmed[item["line_no"]],"description":item["description"],
                      "quantity":item["quantity"]["value"] if item.get("quantity") else None,
                      "unit":item["quantity"]["unit"] if item.get("quantity") else None})
    if not items: return {"error":"No valid human-confirmed ERP codes. Match first and select only suggested codes."}
    terms=[x.model_dump() if hasattr(x,"model_dump") else x for x in body.terms_override] if body.terms_override else _runtime_terms()
    rfq_id=_id("rfq")
    subject=f"Request for Quotation — {req.get('project_name') or 'Project requirement'}"
    body_text=subject+"\n\nPlease quote against the following approved items:\n"+json.dumps(items,indent=2)+"\n\nCommercial terms:\n"+"\n".join(f"{i+1}. {t['text']}" for i,t in enumerate(terms))
    result={"rfq_id":rfq_id,"requirement_id":body.requirement_id,"subject":subject,"body_text":body_text,"items":items,"terms":terms,"response_due_date":body.response_due_date}
    save("rfq",rfq_id,result); return result

async def upload_quotation(rfq_id,vendor_name,filename,content):
    rfq=get("rfq",rfq_id)
    if not rfq: return None
    suffix=Path(filename).suffix.lower()
    if suffix not in {".pdf",".xlsx",".png",".jpg",".jpeg"}: return {"error":"Unsupported file type"}
    safe=f"{_id('upload')}{suffix}"; path=upload_dir()/safe; path.write_bytes(content)
    warnings=[]; extraction="excel"; text=""; vision_trace=[]
    if suffix==".xlsx":
        parsed=parse_excel_quotation(path)
        lines=[{"line_no":i+1,"description":x["description"],"quantity":x["quantity"],"unit":x["unit"],
                "rate":x["rate"],"amount_stated":x["amount_stated"],"evidence":x["evidence"]} for i,x in enumerate(parsed["lines"])]
    else:
        if suffix==".pdf":
            sparse_pages=pdf_sparse_pages(path)
            if sparse_pages and os.getenv("SARVAM_API_KEY"):
                started=__import__("time").monotonic()
                try:
                    provider=SarvamProvider()
                    # Prefer Sarvam Document AI on scanned pages; local OCR is fallback.
                    text=await provider.parse_document(content,filename,"application/pdf")
                    extraction="sarvam_doc_ai"
                    vision_trace.append(AITrace(step="scanned_document_ocr",provider="sarvam-document-ai",model="sarvam-vision-v1",status="ok",attempt=1,
                        latency_ms=int((__import__("time").monotonic()-started)*1000)))
                except Exception as exc:
                    vision_trace.append(AITrace(step="scanned_document_ocr",provider="sarvam-document-ai",model="sarvam-vision-v1",status="failed",attempt=1,
                        latency_ms=int((__import__("time").monotonic()-started)*1000),error=str(exc)[:180]))
                    warnings.append("Sarvam Document AI failed; local text/OCR fallback used: "+str(exc)[:160])
                    text,extraction=pdf_text(path)
            else:
                text,extraction=pdf_text(path)
            if extraction=="scanned_pdf_ocr" and not text.strip():
                warnings.append("Scanned PDF could not be OCR-read. Install Tesseract and Poppler or configure Sarvam API.")
        else:
            if os.getenv("SARVAM_API_KEY"):
                started=__import__("time").monotonic()
                try:
                    mime="image/png" if suffix==".png" else "image/jpeg"
                    text=await SarvamProvider().parse_document(content,filename,mime)
                    extraction="sarvam_doc_ai"
                    vision_trace.append(AITrace(step="image_document_ocr",provider="sarvam-document-ai",model="sarvam-vision-v1",status="ok",attempt=1,
                        latency_ms=int((__import__("time").monotonic()-started)*1000)))
                except Exception as exc:
                    vision_trace.append(AITrace(step="image_document_ocr",provider="sarvam-document-ai",model="sarvam-vision-v1",status="failed",attempt=1,
                        latency_ms=int((__import__("time").monotonic()-started)*1000),error=str(exc)[:180]))
                    warnings.append("Sarvam Document AI failed; local OCR fallback used: "+str(exc)[:160])
            if not text:
                from PIL import Image
                import pytesseract
                text=pytesseract.image_to_string(Image.open(path)); extraction="image_ocr"
        parsed=parse_quote_text(text,filename)
        lines=parsed["lines"]
        if os.getenv("SARVAM_API_KEY") and text.strip():
            schema={
                "type":"object",
                "properties":{
                    "quote_date":{"type":["string","null"],"description":"Printed quotation date in ISO YYYY-MM-DD, null if not present."},
                    "gst_basis":{"type":"string","enum":["extra","inclusive","unstated"],"description":"Whether GST is extra, included, or not stated."},
                    "gst_rate_percent":{"type":["string","null"],"description":"Printed GST percentage only, null if absent."},
                    "gst_page":{"type":["integer","null"],"description":"Page number containing GST wording, null if absent."},
                    "gst_evidence_snippet":{"type":["string","null"],"description":"Exact short source snippet for GST wording."},
                    "lines":{"type":"array","description":"Every quotation line item; do not calculate or fill missing values.",
                        "items":{"type":"object","properties":{
                            "description":{"type":"string","description":"Exact printed line item description."},
                            "quantity":{"type":["string","null"],"description":"Printed quantity exactly, null if absent."},
                            "unit":{"type":["string","null"],"description":"Printed unit exactly, null if absent."},
                            "rate":{"type":["string","null"],"description":"Printed rate exactly, null if absent."},
                            "amount_stated":{"type":["string","null"],"description":"Printed amount exactly, null if absent."},
                            "page":{"type":["integer","null"],"description":"Source PDF page number."},
                            "evidence_snippet":{"type":["string","null"],"description":"Exact short snippet supporting this row."}},
                            "required":["description","quantity","unit","rate","amount_stated","page","evidence_snippet"],"additionalProperties":False}},
                    "terms":{"type":"array","description":"Commercial terms explicitly printed in the quotation.",
                        "items":{"type":"object","properties":{
                            "key":{"type":"string","enum":["pf_esi_registration","tds","security_deposit","gst_extra","water_electricity_hutment","safety_ppe","other"]},
                            "text":{"type":"string","description":"Exact term wording."},
                            "page":{"type":["integer","null"],"description":"Source page number."},
                            "evidence_snippet":{"type":["string","null"],"description":"Exact short evidence snippet."}},
                            "required":["key","text","page","evidence_snippet"],"additionalProperties":False}}
                },
                "required":["quote_date","gst_basis","gst_rate_percent","gst_page","gst_evidence_snippet","lines","terms"],
                "additionalProperties":False}
            def deterministic_quote():
                return {"quote_date":parsed.get("quote_date"),"gst_basis":parsed.get("gst",{}).get("basis","unstated"),
                    "gst_rate_percent":parsed.get("gst",{}).get("rate_percent"),"gst_page":None,"gst_evidence_snippet":None,
                    "lines":[{"description":x["description"],"quantity":x.get("quantity"),"unit":x.get("unit"),
                        "rate":x.get("rate"),"amount_stated":x.get("amount_stated"),
                        "page":(x.get("evidence") or {}).get("page"),"evidence_snippet":(x.get("evidence") or {}).get("snippet")} for x in lines],
                    "terms":[{"key":x["key"],"text":x["text"],"page":(x.get("evidence") or {}).get("page"),
                        "evidence_snippet":(x.get("evidence") or {}).get("snippet")} for x in parsed.get("terms",[])]}
            gateway=AIGateway(SarvamProvider())
            prompt=("Extract quotation facts only. Do not calculate, normalise units, compare prices, infer GST, or invent missing fields. "
                    "For every extracted line and term include its source page and a short exact evidence snippet. "
                    "Use null for absent values. The following is source text with page markers:\\n"+text)
            structured,ai_traces=await gateway.structured(
                "quotation_extraction",prompt,schema,
                lambda value: AIQuoteExtraction.model_validate(value).model_dump(),
                deterministic_quote)
            parsed={"quote_date":structured.get("quote_date"),
                "gst":{"basis":structured["gst_basis"],"rate_percent":structured.get("gst_rate_percent"),
                       "evidence":[{"document":filename,"page":structured.get("gst_page"),"snippet":structured.get("gst_evidence_snippet")}]
                       if structured.get("gst_page") or structured.get("gst_evidence_snippet") else []},
                "lines":[{"description":x["description"],"quantity":x.get("quantity"),"unit":x.get("unit"),
                    "rate":x.get("rate"),"amount_stated":x.get("amount_stated"),
                    "evidence":{"document":filename,"page":x.get("page"),"snippet":x.get("evidence_snippet")}}
                    for x in structured["lines"]],
                "terms":[{"key":x["key"],"text":x["text"],"evidence":{"document":filename,"page":x.get("page"),"snippet":x.get("evidence_snippet")}}
                    for x in structured["terms"]]}
            lines=parsed["lines"]
            ai_trace=[x.model_dump() for x in vision_trace+ai_traces]
            if any(x.provider=="sarvam" and x.status in {"ok","repaired"} for x in ai_traces):
                extraction=extraction+"+sarvam_structured"
        else:
            ai_trace=[x.model_dump() for x in vision_trace]+[{"step":"quotation_extract","provider":"deterministic-parser","status":"fallback","attempt":1}]
        if not lines: warnings.append("No quotation line items could be parsed; manual review required.")
    parsed=parsed if suffix!=".xlsx" else parsed
    if not parsed.get("quote_date"):
        warnings.append("Quotation date not detected; date validity is UNKNOWN.")
    # Preserve user-entered vendor identity; do not infer it from file contents.
    standard=_runtime_terms()
    vendor_terms={t.get("key"):t for t in parsed.get("terms",[])}
    from difflib import SequenceMatcher
    deviations=[]
    for standard_term in standard:
        vt=vendor_terms.get(standard_term["key"])
        if not vt:
            deviations.append({"key":standard_term["key"],"status":"not_stated","standard_text":standard_term["text"],"vendor_text":None,"evidence":None})
        else:
            similarity=SequenceMatcher(None,standard_term["text"].lower(),vt["text"].lower()).ratio()
            deviations.append({"key":standard_term["key"],"status":"accepted" if similarity>=0.75 else "deviation",
                "standard_text":standard_term["text"],"vendor_text":vt["text"],"evidence":vt.get("evidence")})
    result={"quotation_id":_id("quo"),"rfq_id":rfq_id,"vendor_name":vendor_name,"source_file":filename,
            "extraction_method":extraction,"quote_date":parsed.get("quote_date"),"validity_text":None,
            "gst":parsed.get("gst",{"basis":"unstated","rate_percent":None}),"lines":lines,
            "terms":parsed.get("terms",[]),"term_deviations":deviations,"extraction_confidence":None,"warnings":warnings,
            "ai_trace":ai_trace if suffix!=".xlsx" else [{"step":"quotation_extract","provider":"deterministic-parser","status":"fallback","attempt":1}]}
    # Deterministic quote-line mapping. Non-exact weak matches stay reviewable.
    from difflib import SequenceMatcher
    def wordset(value):
        return set(re.findall(r"[a-z0-9]+",str(value).lower()))
    for line in result["lines"]:
        scored=[]
        for item in rfq["items"]:
            a=wordset(line["description"]); b=wordset(item["description"])
            overlap=len(a & b)/max(1,len(a | b))
            seq=SequenceMatcher(None,line["description"].lower(),item["description"].lower()).ratio()
            score=round(0.65*overlap+0.35*seq,4)
            scored.append((score,item))
        if scored:
            score,item=max(scored,key=lambda x:x[0])
            if score>=0.35:
                line["rfq_line_no"]=item["line_no"]
                line["match_confidence"]=score
                line["match_status"]="exact" if line["description"].strip().casefold()==item["description"].strip().casefold() else ("candidate" if score>=0.72 else "needs_review")
    save("quotation",result["quotation_id"],result); return result

def shortlist(comparison_id, rules=None):
    cmp=get("comparison",comparison_id)
    if not cmp: return None
    rules=rules or {}
    max_vendors=int(rules.get("max_vendors",3))
    exclude_on_blocking=bool(rules.get("exclude_on_blocking_flags",True))
    reject_terms=set(rules.get("exclude_if_term_rejected",[]))
    ranked=[]; pending=[]; excluded=[]
    for v in cmp["vendors"]:
        reasons=[]; caveats=[]
        if v["total_incl_gst"] is None or v["lines_needs_review"] or v["lines_not_quoted"]:
            pending.append({"quotation_id":v["quotation_id"],"vendor_name":v["vendor_name"],
                "reasons":["Not fully comparable or GST-inclusive total is UNKNOWN."]})
            continue
        blocking=[f for f in v["flags"] if f["severity"]=="blocking"]
        if blocking and exclude_on_blocking:
            excluded.append({"quotation_id":v["quotation_id"],"vendor_name":v["vendor_name"],"reasons":[x["message"] for x in blocking]})
            continue
        rejected=[d for d in v.get("term_deviations",[]) if d.get("key") in reject_terms and d.get("status")!="accepted"]
        if rejected:
            excluded.append({"quotation_id":v["quotation_id"],"vendor_name":v["vendor_name"],
                "reasons":[f"Commercial term {d.get('key')} is {d.get('status')}." for d in rejected]})
            continue
        vendor_evidence=[e for row in cmp["rows"] for cell in row["cells"]
                         if cell["quotation_id"]==v["quotation_id"] for e in cell.get("evidence",[])]
        reasons.append({"text":"All RFQ lines are comparable on the confirmed basis.","evidence":vendor_evidence})
        reasons.append({"text":"GST-inclusive total is available from explicitly stated GST basis.","evidence":vendor_evidence})
        for deviation in v.get("term_deviations",[]):
            if deviation.get("status") in {"deviation","not_stated"}:
                caveats.append(f"Commercial term {deviation.get('key')}: {deviation.get('status')}.")
        caveats.extend(f["message"] for f in v["flags"] if f["severity"]=="warning")
        ranked.append({"quotation_id":v["quotation_id"],"vendor_name":v["vendor_name"],"total_incl_gst":v["total_incl_gst"],"reasons":reasons,"caveats":caveats})
    ranked.sort(key=lambda x:Decimal(x["total_incl_gst"]))
    for i,x in enumerate(ranked,1): x["rank"]=i
    rules_applied={"max_vendors":max_vendors,"exclude_on_blocking_flags":exclude_on_blocking,
                   "exclude_if_term_rejected":sorted(reject_terms)}
    ranked=ranked[:max_vendors]
    result={"comparison_id":comparison_id,"rules_applied":rules_applied,"shortlist":ranked,
            "pending_review":pending,"excluded":excluded,"decision_support_only":True}
    save("shortlist",comparison_id,result); return result


def generate_comparison(rfq, quotations, resolutions):
    resolutions=[x.model_dump() if hasattr(x,"model_dump") else x for x in resolutions]
    result=build_comparison(rfq,quotations,resolutions)
    save("comparison",result["comparison_id"],result)
    return result


def get_record(kind: str, ident: str):
    return get(kind, ident)

def save_record(kind: str, ident: str, payload: dict):
    save(kind, ident, payload)

def store_boq_upload(content: bytes) -> Path:
    path=upload_dir()/("boq_"+uuid4().hex+".xlsx")
    path.write_bytes(content)
    return path

def generate_comparison_for_ids(rfq_id: str, quotation_ids: list[str], resolutions: list[dict]):
    from app.core.errors import AppError
    rfq=get("rfq",rfq_id)
    if not rfq: raise AppError("NOT_FOUND","RFQ not found",404)
    quotes=[]
    for qid in quotation_ids:
        q=get("quotation",qid)
        if not q: raise AppError("NOT_FOUND",f"Quotation {qid} not found",404)
        if q["rfq_id"]!=rfq_id: raise AppError("CONFLICT_STATE","Quotation belongs to another RFQ",409)
        quotes.append(q)
    return generate_comparison(rfq,quotes,resolutions)

def create_approval(comparison_id: str, body):
    from app.core.errors import AppError
    cmp=get("comparison",comparison_id)
    if not cmp: raise AppError("NOT_FOUND","Comparison not found",404)
    if get("approval",comparison_id): raise AppError("CONFLICT_STATE","Decision already recorded",409)
    selected=body.selected_quotation_id
    vendor=None
    if body.decision in {"approve","override"} and not selected:
        raise AppError("VALIDATION_ERROR","A selected quotation is required",422)
    if body.decision=="reject_all" and selected:
        raise AppError("VALIDATION_ERROR","reject_all must not select a vendor",422)
    if body.decision=="override" and not (body.override_reason or "").strip():
        raise AppError("OVERRIDE_REASON_REQUIRED","Override reason is required",422)
    if selected:
        vendor=next((v for v in cmp["vendors"] if v["quotation_id"]==selected),None)
        if not vendor: raise AppError("NOT_FOUND","Selected quotation not found in comparison",404)
    if body.decision=="approve":
        sl=get("shortlist",comparison_id)
        if not sl or not any(x["quotation_id"]==selected for x in sl["shortlist"]):
            raise AppError("VALIDATION_ERROR","Approve requires a shortlisted quotation; use override with a reason otherwise",422)
    note=f"Decision: {body.decision}. Approver: {body.approver_name}. "
    if vendor: note+=f"Selected vendor: {vendor['vendor_name']}. Evaluated total: {vendor.get('total_incl_gst') or 'UNKNOWN'}. "
    if body.override_reason: note+=f"Override reason: {body.override_reason}. "
    if body.note: note+=f"Additional note: {body.note}"
    from datetime import datetime,timezone
    result={"approval_id":_id("apr"),"comparison_id":comparison_id,"decision":body.decision,
        "selected_quotation_id":selected,"vendor_name":vendor["vendor_name"] if vendor else None,
        "is_override":body.decision=="override","approval_note":note,"approver_name":body.approver_name,
        "decided_at":datetime.now(timezone.utc).isoformat()}
    save("approval",comparison_id,result)
    return result


def load_demo():
    # Fully synthetic demo fixture. No company data, API key or internet required.
    req_id="req_demo"
    req={"requirement_id":req_id,"project_name":"Synthetic Residential Project","scope_summary":"Synthetic waterproofing requirement for demonstration.",
         "items":[
            {"line_no":1,"description":"Synthetic waterproofing to floor","quantity":{"value":"1000","unit":"SQFT"},"source":{"document":"synthetic_demo.xlsx","locator":"BOQ!A2:C2"},"flags":[]},
            {"line_no":2,"description":"Synthetic waterproofing to wall","quantity":{"value":"500","unit":"SQFT"},"source":{"document":"synthetic_demo.xlsx","locator":"BOQ!A3:C3"},"flags":[]}
         ],"note":None,"warnings":["SYNTHETIC DEMO DATA — not real vendor or company information."],
         "ai_trace":[{"step":"demo","provider":"synthetic-cache","status":"cached","attempt":1}]}
    save("requirement",req_id,req)
    matches={"requirement_id":req_id,"matches":[
        {"line_no":1,"status":"matched","confirmed_code":"SYN-WP-001","suggestions":[{"item_code":"SYN-WP-001","description":"Synthetic floor waterproofing","erp_unit":"SQFT","confidence":0.94,"rationale":"Synthetic fixture match.","near_duplicates":[]}],"flags":[]},
        {"line_no":2,"status":"matched","confirmed_code":"SYN-WP-002","suggestions":[{"item_code":"SYN-WP-002","description":"Synthetic wall waterproofing","erp_unit":"SQFT","confidence":0.91,"rationale":"Synthetic fixture match.","near_duplicates":[]}],"flags":[]}
    ],"ai_trace":[{"step":"demo_match","provider":"synthetic-cache","status":"cached","attempt":1}]}
    save("matches",req_id,matches)
    rfq_id="rfq_demo"
    terms=[{"key":"pf_esi_registration","text":"SAMPLE: Contractor to provide applicable statutory registration documents."},
           {"key":"tds","text":"SAMPLE: Applicable tax deductions will be made as per law."},
           {"key":"security_deposit","text":"SAMPLE: Security deposit percentage and release terms to be confirmed."},
           {"key":"gst_extra","text":"SAMPLE: GST treatment must be explicitly stated in the quotation."},
           {"key":"water_electricity_hutment","text":"SAMPLE: Site utilities and facilities to be confirmed in writing."},
           {"key":"safety_ppe","text":"SAMPLE: Contractor is responsible for required safety equipment."}]
    rfq={"rfq_id":rfq_id,"requirement_id":req_id,"subject":"SAMPLE RFQ — Synthetic Project",
         "body_text":"SYNTHETIC DEMO RFQ — not a real tender.\n\n"+json.dumps(terms,indent=2),
         "items":[{"line_no":1,"item_code":"SYN-WP-001","description":"Synthetic waterproofing to floor","quantity":"1000","unit":"SQFT"},
                  {"line_no":2,"item_code":"SYN-WP-002","description":"Synthetic waterproofing to wall","quantity":"500","unit":"SQFT"}],"terms":terms}
    save("rfq",rfq_id,rfq)
    quote_data=[
        ("Synthetic Vendor A",["31.00","28.00"],"extra","18"),
        ("Synthetic Vendor B",["33.00","29.00"],"inclusive",None),
        ("Synthetic Vendor C",["30.00","27.00"],"unstated",None),
        ("Synthetic Vendor D",["32.00","28.50"],"extra","18")]
    qids=[]
    for idx,(name,rates,basis,gst_rate) in enumerate(quote_data,1):
        qid=f"quo_demo_{idx}"; qids.append(qid)
        lines=[]
        for j,(desc,qty,rate) in enumerate([("Synthetic waterproofing to floor","1000",rates[0]),("Synthetic waterproofing to wall","500",rates[1])],1):
            lines.append({"rfq_line_no":j,"description":desc,"quantity":qty,"unit":"SQFT","rate":rate,
                          "amount_stated":str((Decimal(qty)*Decimal(rate)).quantize(Decimal("0.01"))),"evidence":{"document":f"synthetic_quote_{idx}.pdf","page":1,"snippet":f"{desc} | SQFT | {qty} | {rate}"}})
        extraction_method={1:"synthetic_text_pdf",2:"synthetic_excel",3:"synthetic_alternate_layout",4:"synthetic_scanned_ocr"}[idx]
        quote={"quotation_id":qid,"rfq_id":rfq_id,"vendor_name":name,"source_file":f"synthetic_quote_{idx}.pdf",
            "extraction_method":extraction_method,"quote_date":"2026-11-20","gst":{"basis":basis,"rate_percent":gst_rate},
            "lines":lines,"terms":[],"warnings":["Synthetic demonstration quotation; no real vendor data."],
            "ai_trace":[{"step":"quotation_extract","provider":"synthetic-cache","status":"cached","attempt":1}]}
        save("quotation",qid,quote)
    cmp=generate_comparison(rfq,[get("quotation",x) for x in qids],[])
    sl=shortlist(cmp["comparison_id"])
    return {"requirement":req,"matches":matches,"rfq":rfq,"quotations":[get("quotation",x) for x in qids],
            "comparison":cmp,"shortlist":sl,"message":"Synthetic demo data loaded. No external API calls were made."}


def health_status():
    try:
        con=connect()
        con.execute("SELECT 1")
        con.close()
        db_status="ok"
    except Exception:
        db_status="error"
    return {"status":"ok" if db_status=="ok" else "degraded","version":APP_VERSION,
            "database":db_status,"ai":{"primary_configured":bool(SARVAM_API_KEY),
            "fallback_configured":False,"cached_samples_enabled":AI_USE_CACHED_SAMPLES}}
