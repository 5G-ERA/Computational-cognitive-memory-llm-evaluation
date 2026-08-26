from __future__ import annotations
import json,time,random,re
from pathlib import Path
from qa_core import parse_final_answer

RETRYABLE_HTTP={429,500,502,503,504}
CLIENT_ERROR_HTTP={400,401,403,404,405,413,422}
CONTEXT_PATTERNS=re.compile(r'context (length|window)|n_ctx|too many tokens|maximum context',re.I)

def http_status(exc):
    code=getattr(exc,'code',None)
    if isinstance(code,int):return code
    m=re.search(r'\b(4\d{2}|5\d{2})\b',str(exc))
    return int(m.group(1)) if m else None

def is_retryable(exc):
    code=http_status(exc)
    if code is not None:return code in RETRYABLE_HTTP
    s=(type(exc).__name__+' '+str(exc)).lower()
    return any(k in s for k in ('timeout','connection','temporarily','reset by peer','urlerror'))

def classify_terminal(exc):
    """Terminal classification for a fault that must NOT be retried."""
    code=http_status(exc);s=str(exc)
    if CONTEXT_PATTERNS.search(s) or code==413:return 'TRANSPORT_CONTEXT_LIMIT'
    if code in CLIENT_ERROR_HTTP:return 'CLIENT_CONFIGURATION_ERROR'
    return None

def classify_exhausted(exc):
    code=http_status(exc);s=(type(exc).__name__+' '+str(exc)).lower()
    if code==429 or 'rate' in s:return 'TRANSPORT_RATE_LIMIT_EXHAUSTED'
    if 'timeout' in s:return 'TRANSPORT_TIMEOUT_EXHAUSTED'
    return 'TRANSPORT_SERVER_ERROR_EXHAUSTED'

TERMINAL_PREFIXES=('COMPLETED','MODEL_')
TERMINAL_EXACT={'TRANSPORT_CONTEXT_LIMIT','CLIENT_CONFIGURATION_ERROR'}

def run_calls(calls, adapter, out_dir, retry_policy, require_end_marker=True, on_record=None):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    reg=out/'call_registry.jsonl';attempts=out/'attempts.jsonl';raw=out/'responses_raw.jsonl';parsed=out/'responses_parsed.jsonl'
    terminal={}
    if reg.exists():
        for line in reg.open():
            r=json.loads(line);st=r.get('terminal_status') or ''
            if st.startswith(TERMINAL_PREFIXES) or st in TERMINAL_EXACT:
                terminal[r['call_id']]=r
    rng=random.Random(retry_policy.get('jitter_seed',0))
    max_attempts=int(retry_policy.get('max_attempts',3))
    if max_attempts<1:raise ValueError('retry_policy.max_attempts must be >= 1')
    with attempts.open('a') as af,raw.open('a') as rf,parsed.open('a') as pf,reg.open('a') as gf:
        for call in calls:
            cid=call['call_id']
            if cid in terminal:continue
            final=None;obj=None
            for attempt in range(1,max_attempts+1):
                try:
                    resp=adapter.invoke(call)
                    rf.write(json.dumps({'call_id':cid,'attempt':attempt,**resp})+'\n');rf.flush()
                    pr=parse_final_answer(resp.get('assistant_text',''),resp.get('structured_object'),
                                          finish_reason=resp.get('finish_reason'),require_end_marker=require_end_marker)
                    obj=pr.obj
                    pf.write(json.dumps({'call_id':cid,'status':pr.status,'parsed':pr.obj,'errors':pr.errors,
                                         'finish_reason':resp.get('finish_reason')})+'\n');pf.flush()
                    final=pr.status
                    af.write(json.dumps({'call_id':cid,'attempt':attempt,'outcome':final})+'\n');af.flush()
                    break
                except Exception as exc:
                    hard=classify_terminal(exc)
                    if hard and not is_retryable(exc):
                        final=hard
                        af.write(json.dumps({'call_id':cid,'attempt':attempt,'outcome':final,'error':str(exc),'retryable':False})+'\n');af.flush()
                        break
                    af.write(json.dumps({'call_id':cid,'attempt':attempt,'outcome':'RETRYABLE_ERROR','error':str(exc)})+'\n');af.flush()
                    if attempt<max_attempts:
                        b=retry_policy['backoff_seconds'];delay=b[min(attempt,len(b)-1)]+rng.random()*.05
                        time.sleep(delay)
                    else:
                        final=classify_exhausted(exc)
            restartable = bool(final) and final.startswith('TRANSPORT_') and final not in TERMINAL_EXACT \
                          and retry_policy.get('failed_retryable_calls_are_restartable',True)
            if restartable:
                af.write(json.dumps({'call_id':cid,'attempt':max_attempts,'outcome':final,'restartable':True})+'\n');af.flush()
            else:
                rec={'call_id':cid,'terminal_status':final}
                if on_record:rec.update(on_record(call,obj,final) or {})
                gf.write(json.dumps(rec)+'\n');gf.flush()
    return validate_completion(calls,out)

def validate_completion(calls,out_dir):
    out=Path(out_dir);expected={x['call_id'] for x in calls}
    reg=[json.loads(x) for x in open(out/'call_registry.jsonl')] if (out/'call_registry.jsonl').exists() else []
    ids=[x['call_id'] for x in reg]
    report={'expected':len(expected),'terminal':len(set(ids)),'all_expected_terminal':set(ids)==expected,
            'no_duplicate_terminal':len(ids)==len(set(ids)),'pass':set(ids)==expected and len(ids)==len(set(ids))}
    json.dump(report,open(out/'run_completion_report.json','w'),indent=2);return report
