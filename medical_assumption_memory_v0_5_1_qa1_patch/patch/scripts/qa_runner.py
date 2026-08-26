import json,time,random
from pathlib import Path
from qa_core import parse_final_answer

RETRYABLE_HTTP={429,500,502,503,504}

def classify_transport(exc):
    s=(type(exc).__name__+' '+str(exc)).lower()
    if '429' in s or 'rate' in s:return 'TRANSPORT_RATE_LIMIT_EXHAUSTED'
    if 'timeout' in s:return 'TRANSPORT_TIMEOUT_EXHAUSTED'
    return 'TRANSPORT_SERVER_ERROR_EXHAUSTED'

def run_calls(calls, adapter, out_dir, retry_policy, require_end_marker=True):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    reg=out/'call_registry.jsonl';attempts=out/'attempts.jsonl';raw=out/'responses_raw.jsonl';parsed=out/'responses_parsed.jsonl'
    terminal={}
    if reg.exists():
        for line in reg.open():
            r=json.loads(line)
            if r['terminal_status'].startswith('COMPLETED') or r['terminal_status'].startswith('MODEL_') or r['terminal_status'] in ('TRANSPORT_CONTEXT_LIMIT','CLIENT_CONFIGURATION_ERROR'):
                terminal[r['call_id']]=r
    rng=random.Random(retry_policy.get('jitter_seed',0))
    with attempts.open('a') as af,raw.open('a') as rf,parsed.open('a') as pf,reg.open('a') as gf:
        for call in calls:
            cid=call['call_id']
            if cid in terminal:continue
            final=None
            for attempt in range(1,retry_policy['max_attempts']+1):
                try:
                    resp=adapter.invoke(call)
                    rf.write(json.dumps({'call_id':cid,'attempt':attempt,**resp})+'\n');rf.flush()
                    pr=parse_final_answer(resp.get('assistant_text',''),resp.get('structured_object'),require_end_marker=require_end_marker)
                    pf.write(json.dumps({'call_id':cid,'status':pr.status,'parsed':pr.obj,'errors':pr.errors})+'\n');pf.flush()
                    final=pr.status
                    af.write(json.dumps({'call_id':cid,'attempt':attempt,'outcome':final})+'\n');af.flush()
                    break
                except Exception as exc:
                    af.write(json.dumps({'call_id':cid,'attempt':attempt,'outcome':'RETRYABLE_ERROR','error':str(exc)})+'\n');af.flush()
                    if attempt<retry_policy['max_attempts']:
                        delay=retry_policy['backoff_seconds'][min(attempt,len(retry_policy['backoff_seconds'])-1)] + rng.random()*.05
                        time.sleep(delay)
                    else: final=classify_transport(exc)
            restartable = final and final.startswith('TRANSPORT_') and retry_policy.get('failed_retryable_calls_are_restartable', True)
            if restartable:
                af.write(json.dumps({'call_id':cid,'attempt':retry_policy['max_attempts'],'outcome':final,'restartable':True})+'\n');af.flush()
            else:
                gf.write(json.dumps({'call_id':cid,'terminal_status':final})+'\n');gf.flush()
    return validate_completion(calls,out)

def validate_completion(calls,out_dir):
    out=Path(out_dir);expected={x['call_id'] for x in calls};reg=[json.loads(x) for x in open(out/'call_registry.jsonl')];ids=[x['call_id'] for x in reg]
    report={'expected':len(expected),'terminal':len(set(ids)),'all_expected_terminal':set(ids)==expected,'no_duplicate_terminal':len(ids)==len(set(ids)),'pass':set(ids)==expected and len(ids)==len(set(ids))}
    json.dump(report,open(out/'run_completion_report.json','w'),indent=2);return report
