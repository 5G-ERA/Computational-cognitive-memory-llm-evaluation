import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from core import parse,schema_errors,interpret
valid={'reaction':'WAIT_FOR_EVIDENCE','rule_id':'R02_EVIDENCE_INCOMPLETE','decisive_event_ids':['EVT-0000001'],'reason':'Evidence is incomplete.'}
assert schema_errors(valid)==[]
assert schema_errors({**valid,'rule_id':'BAD'})
assert parse(json.dumps(valid))[0]==valid
assert parse('{bad')[0] is None
print('test_core PASS')
