"""qa1b regression suite: Renxi's qa1 tests plus the eight cases they did not cover."""
from __future__ import annotations
import json,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Runs both from the overlay layout (patch/scripts) and from a package the overlay was
# applied to (scripts/), so the same suite gates the release candidate.
BASE=ROOT/'patch' if (ROOT/'patch/scripts/qa_core.py').exists() else ROOT
sys.path.insert(0,str(BASE/'scripts'))
from qa_core import parse_final_answer,revised_grounding,certified_meta_decision_accuracy,chance_deviation_gate
from qa_runner import run_calls
policy=json.load(open(BASE/'config/retry_policy.json'));policy['backoff_seconds']=[0,0,0]

# --- original qa1 assertions that must keep holding -------------------------------
text='draft {"reaction":"TAILOR_SUPPORT"} but reconsidered </think> {"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"final"}'
r=parse_final_answer(text);assert r.status=='COMPLETED_VALID' and r.obj['reaction']=='CONTINUE_SUPPORT'
assert parse_final_answer('</think> {"a":1} {"b":2}').status=='COMPLETED_INVALID_JSON'
assert not chance_deviation_gate(0.0,8)['pass']
assert not chance_deviation_gate(.50,40)['pass']
assert chance_deviation_gate(.1667,32)['pass']

# --- D1 the real Kimi-Dev-72B marker is accepted ----------------------------------
KIMI='◁think▷weighing R09 against R10◁/think▷\n\n```json\n{"reaction":"CONTINUE_SUPPORT","rule_id":"R10_CONFIRMED_CONTINUATION","decisive_event_ids":["EVT-0000005"],"reason":"ok"}\n```'
r=parse_final_answer(KIMI,finish_reason='stop')
assert r.status=='COMPLETED_VALID' and r.obj['rule_id']=='R10_CONFIRMED_CONTINUATION',r.status
# drafts inside the Kimi reasoning block are still discarded
d='◁think▷first {"reaction":"TAILOR_SUPPORT"} then no◁/think▷ {"reaction":"CONTINUE_SUPPORT"}'
assert parse_final_answer(d,finish_reason='stop').obj['reaction']=='CONTINUE_SUPPORT'

# --- D2 truncation follows the provider signal, not marker absence ----------------
complete_no_marker='{"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"ok"}'
assert parse_final_answer(complete_no_marker,finish_reason='stop').status=='COMPLETED_VALID'
assert parse_final_answer('◁think▷still reasoning and cut off',finish_reason='length').status=='COMPLETED_OUTPUT_TRUNCATED'
assert parse_final_answer('◁think▷reasoning',finish_reason='stop').status=='COMPLETED_OUTPUT_TRUNCATED'  # unclosed block
assert parse_final_answer('</think> {"reaction":"CONTINUE_SUPP',finish_reason='length').status=='COMPLETED_OUTPUT_TRUNCATED'
assert parse_final_answer('draft {"reaction":"TAILOR_SUPPORT"}',finish_reason='length').status=='COMPLETED_OUTPUT_TRUNCATED'

# --- D3 non-retryable client faults are terminal and typed ------------------------
class Http(Exception):
    def __init__(self,code,msg):super().__init__(f'HTTP Error {code}: {msg}');self.code=code
class Bad:
    def __init__(self,code,msg):self.code=code;self.msg=msg;self.n=0
    def invoke(self,call):self.n+=1;raise Http(self.code,self.msg)
for code,msg,expected in [(401,'Unauthorized','CLIENT_CONFIGURATION_ERROR'),
                          (404,'model not found','CLIENT_CONFIGURATION_ERROR'),
                          (400,'context length exceeded','TRANSPORT_CONTEXT_LIMIT')]:
    tmp=Path(tempfile.mkdtemp());ad=Bad(code,msg)
    rep=run_calls([{'call_id':'C-1'}],ad,tmp,policy)
    reg=[json.loads(x) for x in open(tmp/'call_registry.jsonl')]
    assert ad.n==1,(code,ad.n)                      # not retried
    assert reg[0]['terminal_status']==expected,(code,reg[0])
    assert rep['pass']                              # completeness reachable
    shutil.rmtree(tmp)
# retryable faults still retry and stay restartable
class Flaky:
    def __init__(self):self.n=0
    def invoke(self,call):
        self.n+=1
        if self.n<3:raise Http(503,'Service Unavailable')
        return {'assistant_text':'</think> {"reaction":"CONTINUE_SUPPORT"}','structured_object':None,'finish_reason':'stop'}
tmp=Path(tempfile.mkdtemp());f=Flaky();rep=run_calls([{'call_id':'C-2'}],f,tmp,policy)
assert f.n==3 and rep['pass'];shutil.rmtree(tmp)

# --- D4 grounding requires a hit in each decisive group ---------------------------
hist=['EVT-0000002','EVT-0000003'];curr=['EVT-0000361','EVT-0000362','EVT-0000363']
vis=set(hist+curr)
g_one=revised_grounding({'decisive_event_ids':[curr[0]]},vis,[hist,curr])
assert not g_one['decisive_evidence_hit'] and not certified_meta_decision_accuracy(True,True,True,g_one)
g_both=revised_grounding({'decisive_event_ids':[hist[0],curr[0]]},vis,[hist,curr])
assert g_both['decisive_evidence_hit'] and certified_meta_decision_accuracy(True,True,True,g_both)
assert g_both['provenance_reference_validity']==1
# exhaustive citation is not required
assert revised_grounding({'decisive_event_ids':[hist[1],curr[2]]},vis,[hist,curr])['decisive_evidence_hit']
# invisible citations still fail
assert not revised_grounding({'decisive_event_ids':[hist[0],curr[0],'EVT-9999999']},vis,[hist,curr])['all_citations_visible']

# --- D7 the chance gate reports its own false-alarm rate --------------------------
assert chance_deviation_gate(.1667,32)['expected_false_fail_rate']>.15
assert chance_deviation_gate(.20,200)['expected_false_fail_rate']<.01

# --- runner reliability, as in qa1 -------------------------------------------------
class FaultAdapter:
    def __init__(self):self.n={}
    def invoke(self,call):
        cid=call['call_id'];self.n[cid]=self.n.get(cid,0)+1
        if int(cid.split('-')[-1])%5==0 and self.n[cid]==1:raise TimeoutError('temporary timeout')
        return {'assistant_text':'◁think▷ok◁/think▷ {"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"ok"}','structured_object':None,'finish_reason':'stop'}
calls=[{'call_id':f'CALL-{i:03d}'} for i in range(1,361)]
tmp=Path(tempfile.mkdtemp())
rep=run_calls(calls,FaultAdapter(),tmp,policy);assert rep['pass'] and rep['terminal']==360
att=[json.loads(x) for x in open(tmp/'attempts.jsonl')];assert sum(x['outcome']=='RETRYABLE_ERROR' for x in att)==72
rep2=run_calls(calls,FaultAdapter(),tmp,policy);assert rep2['pass']
reg=[json.loads(x) for x in open(tmp/'call_registry.jsonl')];assert len(reg)==360==len({x['call_id'] for x in reg})
shutil.rmtree(tmp)
class OutageAdapter:
    def invoke(self,call):raise TimeoutError('full outage')
class RecoveryAdapter:
    def invoke(self,call):return {'assistant_text':'◁think▷ok◁/think▷ {"reaction":"CONTINUE_SUPPORT","rule_id":"R10","decisive_event_ids":["EVT-1"],"reason":"ok"}','structured_object':None,'finish_reason':'stop'}
tmp2=Path(tempfile.mkdtemp());small=[{'call_id':f'OUT-{i:03d}'} for i in range(1,73)]
failed=run_calls(small,OutageAdapter(),tmp2,policy);assert not failed['pass'] and failed['terminal']==0
rec=run_calls(small,RecoveryAdapter(),tmp2,policy);assert rec['pass'] and rec['terminal']==72
reg2=[json.loads(x) for x in open(tmp2/'call_registry.jsonl')];assert len(reg2)==72==len({x['call_id'] for x in reg2})
shutil.rmtree(tmp2)
print('PRE_LLM_QA1B_PASS')
