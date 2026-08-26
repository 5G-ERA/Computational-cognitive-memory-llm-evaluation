from __future__ import annotations
import json,re
from dataclasses import dataclass
from pathlib import Path

# Frozen markers. Kimi-Dev-72B (moonshotai_Kimi-Dev-72B-Q4_0.gguf, llama.cpp server)
# emits the unicode pair below, not the HTML-style tags, so both families are listed.
# qa1c: Kimi-Dev-72B occasionally emits the end marker as "◁/think", dropping the closing
# "▷", and then produces a complete valid final object. The frozen qa1b list matched only the
# well-formed form, so those replies were classified COMPLETED_OUTPUT_TRUNCATED and scored
# incorrect under intention-to-evaluate. The tolerant form is listed AFTER the well-formed one
# and is only reached when the well-formed marker is absent; nothing else in the extraction
# contract changes. finish_reason remains authoritative for genuine truncation.
END_MARKERS=("</think>","<|end_of_thought|>","<|end_of_think|>","◁/think▷","◁/think")
START_MARKERS=("<think>","<|begin_of_thought|>","◁think▷")

def load_markers(policy_path=None):
    if policy_path and Path(policy_path).exists():
        p=json.loads(Path(policy_path).read_text())
        return tuple(p.get('end_of_think_markers',END_MARKERS)),tuple(p.get('start_of_think_markers',START_MARKERS))
    return END_MARKERS,START_MARKERS

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

def parse_final_answer(text, structured=None, finish_reason=None, require_end_marker=True,
                       markers=END_MARKERS, start_markers=START_MARKERS):
    """Deterministic extraction of the single final JSON object.

    Truncation is decided by the provider signal (finish_reason == 'length') or by an
    unclosed reasoning block, never by the mere absence of an end-of-think marker.
    """
    if structured is not None and isinstance(structured,dict):
        return ParseResult('COMPLETED_VALID',structured,[])
    if not text or not text.strip():
        return ParseResult('MODEL_EMPTY',None,['EMPTY'])
    truncated = (finish_reason=='length')
    positions=[(text.find(m),m) for m in markers if text.find(m)>=0]
    if positions:
        earliest=min(p for p,_ in positions)
        # longest marker at the earliest position: "◁/think▷" wins over its "◁/think" prefix
        marker=max((m for p,m in positions if p==earliest),key=len)
        pos=earliest
        segment=text[pos+len(marker):].strip()
    else:
        opened=any(m in text for m in start_markers)
        if truncated or (opened and require_end_marker):
            return ParseResult('COMPLETED_OUTPUT_TRUNCATED',None,['END_OF_THINK_MARKER_MISSING'])
        segment=text.strip()          # complete answer emitted without a reasoning block
    objs=_json_objects(segment)
    if not objs:
        status='COMPLETED_OUTPUT_TRUNCATED' if truncated else 'COMPLETED_INVALID_JSON'
        return ParseResult(status,None,['NO_FINAL_OBJECT'])
    if len(objs)>1:
        return ParseResult('COMPLETED_INVALID_JSON',None,[f'EXPECTED_ONE_FINAL_OBJECT_GOT_{len(objs)}'])
    if truncated:
        return ParseResult('COMPLETED_OUTPUT_TRUNCATED',objs[0],['TRUNCATED_AFTER_FINAL_OBJECT'])
    return ParseResult('COMPLETED_VALID',objs[0],[])

def revised_grounding(decision, supplied_ids, decisive_groups, require_all_groups=True):
    """Protocol v0.5.1-qa1 section 6: a non-empty hit is required in EACH decisive group."""
    cited=set(decision.get('decisive_event_ids') or [])
    visible=set(supplied_ids)
    all_visible=bool(cited) and cited.issubset(visible)
    if not decisive_groups:
        decisive_hit=bool(cited)
    else:
        hits=[bool(cited.intersection(set(g))) for g in decisive_groups]
        decisive_hit=all(hits) if require_all_groups else any(hits)
    validity=len(cited&visible)/len(cited) if cited else 0.0
    return {'all_citations_visible':all_visible,'decisive_evidence_hit':decisive_hit,
            'provenance_reference_validity':validity,'group_hits':None if not decisive_groups else hits}

def certified_meta_decision_accuracy(reaction_correct,rule_correct,consistent,grounding):
    return bool(reaction_correct and rule_correct and consistent and grounding['all_citations_visible'] and grounding['decisive_evidence_hit'])

def chance_deviation_gate(accuracy,n_groups,chance=.2,tolerance=.1,min_groups=32,n_items=None,alpha=.05):
    """Two-sided equivalence-style gate around chance.

    The fixed +-0.10 band is retained for continuity but is reported alongside the exact
    binomial false-alarm rate, which is 18.3% at n=32 and therefore not usable alone.
    """
    from math import comb
    n=n_items or n_groups
    false_fail=sum(comb(n,k)*chance**k*(1-chance)**(n-k) for k in range(n+1) if abs(k/n-chance)>tolerance)
    return {'pass':bool(n_groups>=min_groups and abs(accuracy-chance)<=tolerance),
            'accuracy':accuracy,'chance':chance,'absolute_deviation':abs(accuracy-chance),
            'n_groups':n_groups,'tolerance':tolerance,'minimum_groups':min_groups,
            'expected_false_fail_rate':round(false_fail,4)}
