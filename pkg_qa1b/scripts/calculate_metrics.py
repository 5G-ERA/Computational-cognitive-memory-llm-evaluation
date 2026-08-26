import argparse,csv,json,random
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import f1_score,balanced_accuracy_score,accuracy_score
ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();ROOT=Path(__file__).resolve().parents[1]
rows=[json.loads(x) for x in open(Path(a.run)/'scoring_records.jsonl')];ctx={x['context_id']:x for x in csv.DictReader(open(ROOT/'data/current_contexts.csv'))};refs={x['context_id']:x for x in map(json.loads,open(ROOT/'hidden/oracle_references.jsonl'))};labels5=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE']
def metric(q,labels):
 y=[refs[x['context_id']]['oracle_decision']['reaction'] for x in q];p=[x.get('parsed',{}).get('reaction','__INVALID__') if x['status']=='COMPLETED_VALID' else '__INVALID__' for x in q]
 return {'n':len(q),'macro_f1':f1_score(y,p,labels=labels,average='macro',zero_division=0),'balanced_accuracy':balanced_accuracy_score(y,p),'accuracy':accuracy_score(y,p),'rule_accuracy':sum(x.get('rule_correct',False) for x in q)/len(q),'grounded_accuracy':sum(x.get('grounded_correct',False) for x in q)/len(q),'schema_validity':sum(x['status']=='COMPLETED_VALID' for x in q)/len(q)}
out={'primary':{},'full':{}}
for c in ['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY']:
 q=[x for x in rows if x['condition']==c];pri=[x for x in q if ctx[x['context_id']]['transform'] in ('BASE','SECONDARY')];classes=sorted({refs[x['context_id']]['oracle_decision']['reaction'] for x in pri});out['primary'][c]=metric(pri,classes);out['full'][c]=metric(q,labels5)
out['kpis']={'memory_benefit_macro_f1':out['primary']['B1_VERIFIED_MEMORY']['macro_f1']-out['primary']['B0_LLM_ALONE']['macro_f1'],'verification_benefit_macro_f1':out['primary']['B1_VERIFIED_MEMORY']['macro_f1']-out['primary']['M0_OPEN_LOOP_MEMORY']['macro_f1'],'grounded_memory_benefit':out['primary']['B1_VERIFIED_MEMORY']['grounded_accuracy']-out['primary']['B0_LLM_ALONE']['grounded_accuracy'],'rule_memory_benefit':out['primary']['B1_VERIFIED_MEMORY']['rule_accuracy']-out['primary']['B0_LLM_ALONE']['rule_accuracy']}
Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
