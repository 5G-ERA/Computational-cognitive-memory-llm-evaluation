from __future__ import annotations
import argparse,csv,json,random,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from core import schema_errors,interpret,extract_ids
from qa_core import revised_grounding,certified_meta_decision_accuracy
from qa_runner import run_calls
from adapters.mock_adapter import MockAdapter
from adapters.openai_compatible_adapter_qa1 import OpenAICompatibleAdapterQA1

ap=argparse.ArgumentParser()
ap.add_argument('--config',required=True)
ap.add_argument('--split',choices=['development','reserved'],required=True)
ap.add_argument('--output',required=True)
ap.add_argument('--limit',type=int)
a=ap.parse_args()
cfg=json.load(open(a.config))
sp={x['memory_id']:x['split'].lower() for x in csv.DictReader(open(R/'data_v0_5_1/split_manifest.csv'))}
calls=[json.loads(x) for x in open(R/'prompts/model_calls_v0_5_1.jsonl')]
calls=[x for x in calls if sp[x['memory_id']]==a.split]
random.Random(13082652).shuffle(calls)
calls=calls[:a.limit] if a.limit else calls
refs={x['context_id']:x for x in map(json.loads,open(R/'hidden/oracle_references_v0_5_1.jsonl'))}
policy=json.load(open(R/'config/retry_policy.json'))

class _Mock:
    def __init__(self,refs,cfg):self.inner=MockAdapter(refs);self.cfg=cfg
    def invoke(self,call):
        r=self.inner.invoke(call,self.cfg);r.setdefault('finish_reason','stop');return r

adapter=_Mock(refs,cfg) if cfg.get('provider')=='mock' else OpenAICompatibleAdapterQA1(cfg)
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
scoring=open(out/'scoring_records.jsonl','a')

def record(call,obj,status):
    rec={'call_id':call['call_id'],'context_id':call['context_id'],'canonical_id':call['canonical_id'],
         'memory_id':call['memory_id'],'condition':call['condition'],'status':status}
    if obj is not None and status=='COMPLETED_VALID':
        errs=schema_errors(obj)
        if errs:
            rec['status']='COMPLETED_INVALID_SCHEMA';rec['errors']=errs
        else:
            ref=refs[call['context_id']];ev=ref['acceptable_evidence'][call['condition']]
            legacy=interpret(obj,call['payload'],ref,call['condition'])
            g=revised_grounding(obj,extract_ids(call['payload']),
                                ev['historical_groups']+ev['current_groups'],require_all_groups=True)
            rec.update(legacy)
            rec['provenance_reference_validity']=g['provenance_reference_validity']
            rec['decisive_evidence_hit']=g['decisive_evidence_hit']
            rec['certified_meta_decision']=certified_meta_decision_accuracy(
                legacy['reaction_correct'],legacy['rule_correct'],legacy['reaction_rule_consistent'],g)
    rec['parsed']=obj
    scoring.write(json.dumps(rec)+'\n');scoring.flush()
    return {'condition':call['condition'],'memory_id':call['memory_id']}

report=run_calls(calls,adapter,out,policy,on_record=record)
json.dump({'benchmark_version':'0.5.1-qa1','split':a.split,'calls_expected':len(calls),
           'model_config':{k:v for k,v in cfg.items() if 'key' not in k.lower()},
           'call_order_seed':13082652,'completion':report},
          open(out/'run_manifest.json','w'),indent=2)
print(json.dumps(report,indent=2))
sys.exit(0 if report['pass'] else 2)
