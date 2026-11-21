from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from uuid import uuid4

def D(v):
    if v is None or v=="": return None
    try: return Decimal(str(v).replace(",",""))
    except (InvalidOperation,ValueError): return None

def norm_unit(u):
    value=str(u or "").strip().lower().replace(" ","").replace("²","2")
    aliases={"sft":"sqft","soft":"sqft","sqft":"sqft","sq.ft":"sqft","m2":"sqm","sqm":"sqm"}
    return aliases.get(value,value)

def build_comparison(rfq: dict, quotations: list[dict], resolutions: list[dict]):
    rows=[]; vendors=[]; all_flags=[]
    resolution_map={(str(x.get("quotation_id")),int(x.get("rfq_line_no",0))):x for x in resolutions}
    for q in quotations:
        q_cells=[]; subtotal=Decimal("0"); comparable=review=missing=0; vendor_flags=[]
        for item in rfq["items"]:
            line_no=int(item["line_no"]); rfq_qty=D(item["quantity"]); rfq_unit=item["unit"]
            found=next((ln for ln in q.get("lines",[]) if ln.get("rfq_line_no")==line_no),None)
            if found is None:
                found=next((ln for ln in q.get("lines",[]) if ln.get("description","").strip().casefold()==item["description"].strip().casefold()),None)
            flags=[]; evidence=[]
            if not found:
                missing+=1
                flags.append({"code":"ITEM_NOT_QUOTED","severity":"warning","message":"RFQ line not found in quotation.","evidence":[]})
                cell={"quotation_id":q["quotation_id"],"vendor_name":q["vendor_name"],"status":"not_quoted","quoted_quantity":None,"quoted_unit":None,"rate":None,"amount_at_rfq_qty":None,"amount_stated_by_vendor":None,"flags":flags,"evidence":[]}
                q_cells.append(cell); vendor_flags.extend(flags); continue
            evidence=[found["evidence"]] if found.get("evidence") else []
            quoted_qty=D(found.get("quantity")); rate=D(found.get("rate")); stated=D(found.get("amount_stated"))
            unit_mismatch=norm_unit(found.get("unit"))!=norm_unit(rfq_unit)
            qty_unknown=quoted_qty is None or rfq_qty is None
            qty_mismatch=quoted_qty is not None and rfq_qty is not None and quoted_qty!=rfq_qty
            resolution=resolution_map.get((q["quotation_id"],line_no))
            resolved=bool(resolution and D(resolution.get("factor")) and D(resolution.get("factor"))>0 and resolution.get("note") and resolution.get("resolved_by"))
            mapping_review=found.get("match_status")=="needs_review"
            status="comparable"
            if mapping_review and not resolved:
                status="needs_review"; flags.append({"code":"LOW_MATCH_CONFIDENCE","severity":"blocking","message":"Quote line mapping is uncertain; human confirmation required.","evidence":evidence})
            if not found.get("unit"):
                status="needs_review"; flags.append({"code":"UNIT_UNKNOWN","severity":"blocking","message":"Quoted unit is UNKNOWN; human review required.","evidence":evidence})
            elif unit_mismatch and not resolved:
                status="needs_review"; flags.append({"code":"UNIT_MISMATCH","severity":"blocking","message":f"Quoted unit {found.get('unit')} differs from RFQ unit {rfq_unit}; human UnitResolution required.","evidence":evidence})
            if qty_unknown:
                status="needs_review"; flags.append({"code":"QTY_UNKNOWN","severity":"blocking","message":"Quoted or RFQ quantity is UNKNOWN; cannot extend rate safely.","evidence":evidence})
            if qty_mismatch and not resolved:
                status="needs_review"; flags.append({"code":"QTY_MISMATCH","severity":"blocking","message":f"Quoted quantity {quoted_qty} differs from RFQ quantity {rfq_qty}; human confirmation required.","evidence":evidence})
            if rate is None:
                status="needs_review"; flags.append({"code":"MISSING_RATE","severity":"blocking","message":"Rate is missing; cannot compare.","evidence":evidence})
            factor=D(resolution.get("factor")) if resolved else Decimal("1")
            amount=None
            if status=="comparable" and rfq_qty is not None and rate is not None:
                # factor is quoted-unit count per RFQ unit; convert a rate per quoted unit to RFQ unit.
                effective_rate=(rate/factor) if unit_mismatch else rate
                amount=(rfq_qty*effective_rate).quantize(Decimal("0.01"))
                if resolved:
                    flags.append({"code":"HUMAN_RESOLUTION_APPLIED","severity":"info","message":f"Resolution by {resolution['resolved_by']}: {resolution['note']}","evidence":evidence})
                comparable+=1; subtotal+=amount
            elif status=="needs_review": review+=1
            if stated is not None and quoted_qty is not None and rate is not None:
                computed=(quoted_qty*rate).quantize(Decimal("0.01"))
                if computed!=stated.quantize(Decimal("0.01")):
                    flags.append({"code":"ARITHMETIC_MISMATCH","severity":"warning","message":f"Quoted rate × quoted quantity ({computed}) differs from stated amount ({stated}).","evidence":evidence})
            cell={"quotation_id":q["quotation_id"],"vendor_name":q["vendor_name"],"status":status,
                  "quoted_quantity":str(quoted_qty) if quoted_qty is not None else None,"quoted_unit":found.get("unit"),
                  "rate":str(rate) if rate is not None else None,"amount_at_rfq_qty":str(amount) if amount is not None else None,
                  "amount_stated_by_vendor":str(stated) if stated is not None else None,"flags":flags,"evidence":evidence}
            q_cells.append(cell); vendor_flags.extend(flags)
        rows_by_item=q_cells
        if not q.get("quote_date"):
            vendor_flags.append({"code":"QUOTE_DATE_UNKNOWN","severity":"warning","message":"Quotation date was not extracted; validity is UNKNOWN.","evidence":[]})
        for deviation in q.get("term_deviations",[]):
            if deviation.get("status")=="deviation":
                vendor_flags.append({"code":"TERM_DEVIATION","severity":"warning","message":f"Commercial term {deviation.get('key')} differs from RFQ wording.","evidence":[deviation["evidence"]] if deviation.get("evidence") else []})
            elif deviation.get("status")=="not_stated":
                vendor_flags.append({"code":"TERM_NOT_STATED","severity":"warning","message":f"Commercial term {deviation.get('key')} was not found in quotation.","evidence":[]})
        if any(not line.get("rfq_line_no") for line in q.get("lines",[])):
            vendor_flags.append({"code":"EXTRA_ITEM_QUOTED","severity":"warning","message":"One or more quotation lines could not be mapped to an RFQ item.","evidence":[]})
        if any(marker in str(q.get("extraction_method","")) for marker in ("vision","ocr")):
            vendor_flags.append({"code":"LOW_OCR_CONFIDENCE","severity":"warning","message":"OCR-derived values require source-page verification.","evidence":[]})
        if review:
            vendor_flags.append({"code":"UNRESOLVED_REVIEW","severity":"blocking","message":f"{review} line(s) still require human review.","evidence":[]})
        gst=q.get("gst") or {"basis":"unstated","rate_percent":None}
        basis=gst.get("basis","unstated"); gst_rate=D(gst.get("rate_percent"))
        subtotal_out=subtotal if comparable and not review and not missing else None
        gst_amount=total=None
        if subtotal_out is not None:
            if basis=="inclusive":
                gst_amount=Decimal("0.00"); total=subtotal_out
            elif basis=="extra" and gst_rate is not None:
                gst_amount=(subtotal_out*gst_rate/Decimal("100")).quantize(Decimal("0.01")); total=subtotal_out+gst_amount
            else:
                vendor_flags.append({"code":"GST_UNSTATED","severity":"blocking","message":"GST basis/rate is UNKNOWN; inclusive total is null.","evidence":gst.get("evidence",[])})
        else:
            if basis=="unstated" or (basis=="extra" and gst_rate is None):
                vendor_flags.append({"code":"GST_UNSTATED","severity":"blocking","message":"GST basis/rate is UNKNOWN; inclusive total is null.","evidence":gst.get("evidence",[])})
        vendors.append({"quotation_id":q["quotation_id"],"vendor_name":q["vendor_name"],
            "subtotal_comparable":str(subtotal_out) if subtotal_out is not None else None,"gst_basis":basis,
            "gst_rate_percent":str(gst_rate) if gst_rate is not None else None,
            "gst_amount":str(gst_amount) if gst_amount is not None else None,"total_incl_gst":str(total) if total is not None else None,
            "lines_comparable":comparable,"lines_needs_review":review,"lines_not_quoted":missing,
            "term_deviations":q.get("term_deviations",[]),"flags":vendor_flags})
        all_flags.extend(vendor_flags)
        q["_comparison_cells"]=rows_by_item
    for idx,item in enumerate(rfq["items"]):
        rows.append({"rfq_line_no":item["line_no"],"item_code":item.get("item_code"),
            "description":item["description"],"rfq_quantity":{"value":str(item["quantity"]),"unit":item["unit"]},
            "cells":[q["_comparison_cells"][idx] for q in quotations]})
    for q in quotations: q.pop("_comparison_cells",None)
    return {"comparison_id":"cmp_"+uuid4().hex[:12],"rfq_id":rfq["rfq_id"],
        "created_at":datetime.now(timezone.utc).isoformat(),"computed_by":"deterministic",
        "standard_terms":rfq.get("terms",[]),"rows":rows,"vendors":vendors,"flags":all_flags}
