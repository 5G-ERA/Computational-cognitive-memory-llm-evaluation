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
            rec['all_citations_visible']=g['all_citations_visible']
            rec['per_group_decisive_hits']=g['group_hits']
            rec['required_groups']=len(ev['historical_groups'])+len(ev['current_groups'])
            rec['required_groups_hit']=sum(1 for h in (g['group_hits'] or []) if h)
            rec['all_required_groups_covered']=g['decisive_evidence_hit']
            rec['certified_meta_decision']=certified_meta_decision_accuracy(
                legacy['reaction_correct'],legacy['rule_correct'],legacy['reaction_rule_consistent'],g)
            # Release decision section 7: supporting and descriptive provenance measures.
            # decisive-citation validity is ANY acceptable decisive group, not every group.
            cited=set(obj.get('decisive_event_ids') or [])
            hist=set().union(*ev['historical_groups']) if ev['historical_groups'] else set()
            curr=set().union(*ev['current_groups']) if ev['current_groups'] else set()
            rec['decisive_citation_validity']=bool(cited & (hist|curr))
            rec['historical_provenance_hit']=bool(cited & hist)
            rec['current_provenance_hit']=bool(cited & curr)
            rec['dual_source_provenance_completeness']=bool(cited & hist) and bool(cited & curr)
            # Computed for audit continuity only; NOT a confirmatory endpoint in this release.
            rec['certified_meta_decision_non_confirmatory']=rec.pop('certified_meta_decision')
    rec['parsed']=obj
    scoring.write(json.dumps(rec)+'\n');scoring.flush()
    return {'condition':call['condition'],'memory_id':call['memory_id']}

report=run_calls(calls,adapter,out,policy,on_record=record)
json.dump({'benchmark_version':'0.5.1-qa1b','split':a.split,'calls_expected':len(calls),
           'model_config':{k:v for k,v in cfg.items() if 'key' not in k.lower()},
           'call_order_seed':13082652,'retry_policy':policy,
           'terminology':'public/terminology_v0_5_1.json',
           'reporting_config':'config/reporting_config.json','completion':report},
          open(out/'run_manifest.json','w'),indent=2)
print(json.dumps(report,indent=2))
sys.exit(0 if report['pass'] else 2)
