import json,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'patch/scripts'))
from qa_core import parse_final_answer,revised_grounding,certified_meta_decision_accuracy,chance_deviation_gate
from qa_runner import run_calls

# Final-answer extraction rejects draft objects before end-of-think.
text='draft {"reaction":"TAILOR_SUPPORT"} but reconsidered </think> {"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"final"}'
r=parse_final_answer(text);assert r.status=='COMPLETED_VALID' and r.obj['reaction']=='CONTINUE_SUPPORT'
assert parse_final_answer('draft {"reaction":"TAILOR_SUPPORT"}').status=='COMPLETED_OUTPUT_TRUNCATED'
assert parse_final_answer('</think> {"a":1} {"b":2}').status=='COMPLETED_INVALID_JSON'

# Revised grounding rewards precise, valid decisive citation rather than exhaustive citation.
g=revised_grounding({'decisive_event_ids':['E2']},{'E1','E2','E3'},[['E1','E2','E3']]);assert g['all_citations_visible'] and g['decisive_evidence_hit'] and g['provenance_reference_validity']==1
assert certified_meta_decision_accuracy(True,True,True,g)

# Current-only gate is two-sided around chance and needs at least 32 memory groups.
assert chance_deviation_gate(.1667,32)['pass']
assert not chance_deviation_gate(0.0,8)['pass']
assert not chance_deviation_gate(.50,40)['pass']

# Retry test: 72 of 360 fail once, then recover.
class FaultAdapter:
    def __init__(self):self.n={}
    def invoke(self,call):
        cid=call['call_id'];self.n[cid]=self.n.get(cid,0)+1
        if int(cid.split('-')[-1])%5==0 and self.n[cid]==1:raise TimeoutError('temporary timeout')
        return {'assistant_text':'</think> {"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"ok"}','structured_object':None}

calls=[{'call_id':f'CALL-{i:03d}'} for i in range(1,361)]
tmp=Path(tempfile.mkdtemp());policy=json.load(open(ROOT/'patch/config/retry_policy.json'));policy['backoff_seconds']=[0,0,0]
rep=run_calls(calls,FaultAdapter(),tmp,policy);assert rep['pass'] and rep['terminal']==360
attempts=[json.loads(x) for x in open(tmp/'attempts.jsonl')];assert sum(x['outcome']=='RETRYABLE_ERROR' for x in attempts)==72
# Restart has nothing to duplicate.
rep2=run_calls(calls,FaultAdapter(),tmp,policy);assert rep2['pass'];reg=[json.loads(x) for x in open(tmp/'call_registry.jsonl')];assert len(reg)==360
shutil.rmtree(tmp)

# Full outage leaves calls incomplete but restartable; recovery creates one terminal record per call.
class OutageAdapter:
    def invoke(self,call):raise TimeoutError('full outage')
class RecoveryAdapter:
    def invoke(self,call):return {'assistant_text':'</think> {"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"ok"}','structured_object':None}
tmp2=Path(tempfile.mkdtemp());small=[{'call_id':f'OUT-{i:03d}'} for i in range(1,73)]
failed=run_calls(small,OutageAdapter(),tmp2,policy);assert not failed['pass'] and failed['terminal']==0
recovered=run_calls(small,RecoveryAdapter(),tmp2,policy);assert recovered['pass'] and recovered['terminal']==72
reg2=[json.loads(x) for x in open(tmp2/'call_registry.jsonl')];assert len(reg2)==72 and len({x['call_id'] for x in reg2})==72
shutil.rmtree(tmp2)

print('PRE_LLM_QA_PASS')
