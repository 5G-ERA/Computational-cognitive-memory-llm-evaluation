import argparse,csv,json,random,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from core import parse,schema_errors,interpret
from adapters.openai_compatible_adapter import OpenAICompatibleAdapter
ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--split',choices=['development','reserved'],required=True);ap.add_argument('--output',required=True);ap.add_argument('--limit',type=int);a=ap.parse_args();cfg=json.load(open(a.config));sp={x['canonical_id']:x['split'].lower() for x in csv.DictReader(open(R/'data/split_manifest_v0_5.csv'))};calls=[json.loads(x) for x in open(R/'prompts/model_calls_v0_5.jsonl')];calls=[x for x in calls if sp[x['canonical_id']]==a.split];random.Random(13082651).shuffle(calls);calls=calls[:a.limit] if a.limit else calls;refs={x['context_id']:x for x in map(json.loads,open(R/'hidden/oracle_references_v0_5.jsonl'))};out=Path(a.output);out.mkdir(parents=True,exist_ok=True);registry=out/'call_registry.jsonl';done={json.loads(x)['call_id'] for x in open(registry)} if registry.exists() else set();adapter=OpenAICompatibleAdapter()
with open(out/'responses_raw.jsonl','a') as rf,open(out/'scoring_records.jsonl','a') as sf,open(registry,'a') as gf:
 for call in calls:
  if call['call_id'] in done:continue
  try:
   raw=adapter.invoke(call,cfg);rf.write(json.dumps({'call_id':call['call_id'],**raw})+'\n');rf.flush();obj,pe=parse(raw.get('assistant_text',''),raw.get('structured_object'));errs=pe+schema_errors(obj);status='COMPLETED_VALID' if not errs else ('COMPLETED_INVALID_JSON' if pe else 'COMPLETED_INVALID_SCHEMA');rec={'call_id':call['call_id'],'context_id':call['context_id'],'canonical_id':call['canonical_id'],'condition':call['condition'],'status':status,'parsed':obj,'errors':errs};
   if obj:rec.update(interpret(obj,call['payload'],refs[call['context_id']],call['condition']))
   sf.write(json.dumps(rec)+'\n');sf.flush()
  except Exception as e:status='CLIENT_OR_TRANSPORT_ERROR';rec={'call_id':call['call_id'],'status':status,'error':str(e)}
  gf.write(json.dumps({'call_id':call['call_id'],'terminal_status':status})+'\n');gf.flush()
json.dump({'benchmark_version':'0.5','split':a.split,'calls_expected':len(calls),'model_config':cfg,'call_order_seed':13082651},open(out/'run_manifest.json','w'),indent=2)
