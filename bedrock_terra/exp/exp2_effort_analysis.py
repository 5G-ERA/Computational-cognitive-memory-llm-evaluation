#!/usr/bin/env python3
"""EXP2/EXP3: does reasoning_effort change the conservative-default collapse?
Compares accuracy and answer distribution across effort levels on the SAME dev items."""
import json, csv, sys, collections
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
REL=HERE.parent/'release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c'
truth={r['context_id']:r['oracle_reaction'] for r in csv.DictReader((REL/'data_v0_5_1/contexts.csv').open())}
CONDS=['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY']

def load(run):
    d=HERE/'out'/run
    if not (d/'scoring_records.jsonl').exists(): return None
    sc=[json.loads(l) for l in (d/'scoring_records.jsonl').open()]
    pa={json.loads(l)['call_id']:(json.loads(l).get('parsed') or {}) for l in (d/'responses_parsed.jsonl').open()}
    raw={json.loads(l)['call_id']:json.loads(l) for l in (d/'responses_raw.jsonl').open()}
    return [dict(ctx=s['context_id'],cond=s['condition'],truth=truth[s['context_id']],
                 pred=pa[s['call_id']].get('reaction'),status=s['status'],
                 ok=bool(s['status']=='COMPLETED_VALID' and s.get('reaction_correct') and s.get('reaction_rule_consistent',True)),
                 out_tok=raw[s['call_id']].get('output_tokens'),
                 reas=(raw[s['call_id']].get('provider_metadata') or {}).get('reasoning_tokens')) for s in sc]

runs=sys.argv[1:]
res={}
for r in runs:
    rows=load(r)
    if rows is None: print('%s: sin datos todavia'%r); continue
    e={}
    for c in CONDS:
        sub=[x for x in rows if x['cond']==c]
        if not sub: continue
        dist=collections.Counter(x['pred'] for x in sub)
        top,topn=dist.most_common(1)[0]
        e[c]=dict(n=len(sub),acc=round(sum(x['ok'] for x in sub)/len(sub),4),
                  top_answer=top,top_share=round(topn/len(sub),4),
                  invalid=sum(1 for x in sub if x['status']!='COMPLETED_VALID'),
                  out_tokens=round(sum(x['out_tok'] or 0 for x in sub)/len(sub),1),
                  reasoning_tokens=round(sum(x['reas'] or 0 for x in sub)/len(sub),1))
    if 'B1_VERIFIED_MEMORY' in e and 'B0_LLM_ALONE' in e:
        e['B1_minus_B0_pp']=round(100*(e['B1_VERIFIED_MEMORY']['acc']-e['B0_LLM_ALONE']['acc']),2)
    res[r]=e
print(json.dumps(res,indent=1))
Path(HERE/'exp'/('exp2_effort_%s.json'%'_'.join(x.split("_")[-1] for x in runs))).write_text(json.dumps(res,indent=1))
