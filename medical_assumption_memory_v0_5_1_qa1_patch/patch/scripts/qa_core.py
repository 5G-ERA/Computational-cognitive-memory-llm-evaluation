from __future__ import annotations
import json,re
from dataclasses import dataclass

END_MARKERS=("</think>","<|end_of_thought|>","<|end_of_think|>")

@dataclass
class ParseResult:
    status:str
    obj:dict|None
    errors:list

def _json_objects(text):
    dec=json.JSONDecoder(); out=[]; i=0
    while i<len(text):
        j=text.find('{',i)
        if j<0: break
        try:
            obj,end=dec.raw_decode(text[j:])
            if isinstance(obj,dict):out.append(obj)
            i=j+end
        except Exception:
            i=j+1
    return out

def parse_final_answer(text, structured=None, require_end_marker=True, markers=END_MARKERS):
    if structured is not None and isinstance(structured,dict):
        return ParseResult('COMPLETED_VALID',structured,[])
    if not text or not text.strip():
        return ParseResult('MODEL_EMPTY',None,['EMPTY'])
    positions=[(text.find(m),m) for m in markers if text.find(m)>=0]
    if positions:
        pos,marker=min(positions)
        segment=text[pos+len(marker):].strip()
    elif require_end_marker:
        return ParseResult('COMPLETED_OUTPUT_TRUNCATED',None,['END_OF_THINK_MARKER_MISSING'])
    else:
        segment=text.strip()
    objs=_json_objects(segment)
    if len(objs)!=1:
        return ParseResult('COMPLETED_INVALID_JSON',None,[f'EXPECTED_ONE_FINAL_OBJECT_GOT_{len(objs)}'])
    return ParseResult('COMPLETED_VALID',objs[0],[])

def revised_grounding(decision, supplied_ids, decisive_groups):
    cited=set(decision.get('decisive_event_ids') or [])
    visible=set(supplied_ids)
    all_visible=bool(cited) and cited.issubset(visible)
    decisive_hit=any(bool(cited.intersection(set(group))) for group in decisive_groups) if decisive_groups else bool(cited)
    validity=len(cited&visible)/len(cited) if cited else 0.0
    return {'all_citations_visible':all_visible,'decisive_evidence_hit':decisive_hit,'provenance_reference_validity':validity}

def certified_meta_decision_accuracy(reaction_correct,rule_correct,consistent,grounding):
    return bool(reaction_correct and rule_correct and consistent and grounding['all_citations_visible'] and grounding['decisive_evidence_hit'])

def chance_deviation_gate(accuracy,n_groups,chance=.2,tolerance=.1,min_groups=32):
    return {'pass':bool(n_groups>=min_groups and abs(accuracy-chance)<=tolerance),'accuracy':accuracy,'chance':chance,'absolute_deviation':abs(accuracy-chance),'n_groups':n_groups,'tolerance':tolerance,'minimum_groups':min_groups}
