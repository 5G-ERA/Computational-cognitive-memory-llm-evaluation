import argparse,json,csv
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import f1_score,balanced_accuracy_score,accuracy_score
ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();R=Path(__file__).resolve().parents[1];rows=[json.loads(x) for x in open(Path(a.run)/'scoring_records.jsonl')];refs={x['context_id']:x for x in map(json.loads,open(R/'hidden/oracle_references_v0_5_1.jsonl'))};ctx={x['context_id']:x for x in csv.DictReader(open(R/'data_v0_5_1/contexts.csv'))};labels=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE']
def metric(q):
 y=[refs[x['context_id']]['oracle_decision']['reaction'] for x in q];p=[x.get('parsed',{}).get('reaction','__INVALID__') if x['status']=='COMPLETED_VALID' else '__INVALID__' for x in q]
 return {'n':len(q),'macro_f1':f1_score(y,p,labels=labels,average='macro',zero_division=0),'balanced_accuracy':balanced_accuracy_score(y,p),'accuracy':accuracy_score(y,p),'rule_accuracy':sum(x.get('rule_correct',False) for x in q)/len(q),'grounded_accuracy':sum(x.get('grounded_correct',False) for x in q)/len(q),'schema_validity':sum(x['status']=='COMPLETED_VALID' for x in q)/len(q)}
out={'conditions':{},'render_families':{}}
for c in ['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY']:out['conditions'][c]=metric([x for x in rows if x['condition']==c])
for f in ['STRUCTURED','CHRONOLOGICAL','CONCISE']:
 out['render_families'][f]={c:metric([x for x in rows if x['condition']==c and ctx[x['context_id']]['render_family']==f]) for c in ['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY']}
out['kpis']={'memory_benefit':out['conditions']['B1_VERIFIED_MEMORY']['macro_f1']-out['conditions']['B0_LLM_ALONE']['macro_f1'],'verification_benefit':out['conditions']['B1_VERIFIED_MEMORY']['macro_f1']-out['conditions']['M0_OPEN_LOOP_MEMORY']['macro_f1'],'grounded_memory_benefit':out['conditions']['B1_VERIFIED_MEMORY']['grounded_accuracy']-out['conditions']['B0_LLM_ALONE']['grounded_accuracy']}
Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
