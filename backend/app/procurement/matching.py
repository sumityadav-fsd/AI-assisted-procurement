import re
from difflib import SequenceMatcher

def tokens(s):
    return set(re.findall(r"[a-z0-9]+",s.lower()))

def lexical_candidates(description: str, catalogue: list[dict], limit: int=5):
    q=tokens(description)
    ranked=[]
    for item in catalogue:
        t=tokens(item["description"])
        if not t: continue
        overlap=len(q&t)/max(1,len(q|t))
        seq=SequenceMatcher(None,description.lower(),item["description"].lower()).ratio()
        score=round(0.65*overlap+0.35*seq,4)
        if score>=0.12: ranked.append((score,item))
    ranked.sort(key=lambda x:x[0],reverse=True)
    out=[]
    for score,item in ranked[:limit]:
        near=[{"item_code":other["code"],"description":other["description"],"similarity":round(SequenceMatcher(None,item["description"].lower(),other["description"].lower()).ratio(),3)}
              for _,other in ranked if other["code"]!=item["code"] and SequenceMatcher(None,item["description"].lower(),other["description"].lower()).ratio()>=0.78][:3]
        out.append({"item_code":item["code"],"description":item["description"],"erp_unit":item.get("unit"),
                    "confidence":score,"rationale":"Lexical overlap and text similarity; candidate only.",
                    "near_duplicates":near})
    return out
