import csv,json,itertools,re,sys
from pathlib import Path
from collections import Counter,defaultdict
R=Path(__file__).resolve().parents[1];read=lambda p:list(csv.DictReader(open(R/p)))
RX=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE'];rules=json.load(open(R/'public/rule_vocabulary.json'))
def oracle(z):
 if z['review_boundary']=='PRESENT':return 'R01_REVIEW_BOUNDARY'
 if z['evidence_complete']=='INCOMPLETE':return 'R02_EVIDENCE_INCOMPLETE'
 if z['current_relation']=='DIFFERENT_FUNCTION':return 'R03_DIFFERENT_FUNCTION'
 if z['current_relation']=='UNCERTAIN':return 'R04_UNCERTAIN_FUNCTION'
 if z['verification']=='CONTRADICTED':return 'R05_VERIFIED_SUCCESSOR' if z['successor_state']=='VERIFIED' else 'R06_CONTRADICTED_PREDECESSOR'
 if z['verification']=='UNRESOLVED':return 'R07_UNRESOLVED_VERIFICATION'
 if z['verification']=='PARTIALLY_CONFIRMED':return 'R08_PARTIALLY_CONFIRMED'
 if z['secondary_barrier']=='ACTIVE':return 'R09_SECONDARY_BARRIER'
 return 'R10_CONFIRMED_CONTINUATION'
eps=read('data/episodes.csv');ctx=read('data/current_contexts.csv');calls=[json.loads(x) for x in open(R/'prompts/model_calls.jsonl')];refs=[json.loads(x) for x in open(R/'hidden/oracle_references.jsonl')];flags=read('data/challenge_flags.csv');splits=read('data/split_manifest.csv')
checks={'counts':len(eps)==28 and len(ctx)==140 and len(calls)==420 and len(refs)==140,'assumption_balance':set(Counter(x['assumption'] for x in eps).values())=={4},'verification_balance':set(Counter(x['verification'] for x in eps).values())=={7},'condition_balance':set(Counter(x['condition'] for x in calls).values())=={140},'five_contexts_each':set(Counter(x['episode_id'] for x in ctx).values())=={5},'split_7_21':Counter(x['split'] for x in splits)=={'DEVELOPMENT':7,'RESERVED':21}}
checks['oracle_replay']=all(oracle(x['oracle_state'])==x['oracle_decision']['rule_id'] and rules[x['oracle_decision']['rule_id']]['reaction']==x['oracle_decision']['reaction'] for x in refs)
# exhaustive oracle coverage
outs=[]
for v,r,s,e,b,u in itertools.product(['CONFIRMED','PARTIALLY_CONFIRMED','CONTRADICTED','UNRESOLVED'],['SAME_FUNCTION','DIFFERENT_FUNCTION','UNCERTAIN'],['ACTIVE','INACTIVE','UNKNOWN'],['COMPLETE','INCOMPLETE'],['PRESENT','ABSENT'],['NONE','PROSPECTIVE','VERIFIED','CONTRADICTED']):outs.append(oracle({'verification':v,'current_relation':r,'secondary_barrier':s,'evidence_complete':e,'review_boundary':b,'successor_state':u}))
checks['oracle_576_all_rules']=len(outs)==576 and set(outs)==set(rules)
# parity and hierarchy
by=defaultdict(dict)
for x in calls:by[x['context_id']][x['condition']]=x['payload']
parity=hier=public=True
for d in by.values():
 b,m,v=d['B0_LLM_ALONE'],d['M0_OPEN_LOOP_MEMORY'],d['B1_VERIFIED_MEMORY'];parity &= b['longitudinal_records']==m['longitudinal_records']==v['longitudinal_records'] and b['current_records']==m['current_records']==v['current_records'];hier &= 'open_loop_memory' not in b and 'open_loop_memory' in m and 'verified_cognitive_memory' not in m and 'verified_cognitive_memory' in v;public &= b['shared_world_rules']==m['shared_world_rules']==v['shared_world_rules']
checks['raw_parity']=parity;checks['hierarchy']=hier;checks['public_equality']=public
# no reaction tokens in episode-specific visible data
leaks=[]
for x in calls:
 s=json.dumps({k:v for k,v in x['payload'].items() if k not in ('reaction_vocabulary','rule_vocabulary','response_schema','shared_world_rules','task')}).upper()
 for t in RX:
  if re.search(r'\b'+t+r'\b',s):leaks.append((x['call_id'],t))
checks['no_episode_reaction_leak']=not leaks
checks['primary_flags']=all(x['explicit_policy_phrase_present']=='False' and x['oracle_variable_named_directly']=='False' for x in flags if x['primary_candidate']=='True')
errors=[k for k,v in checks.items() if not v];out={'status':'PASS' if not errors else 'FAIL','errors':errors,'checks':checks,'reaction_distribution':dict(Counter(x['oracle_decision']['reaction'] for x in refs)),'primary_reactions':dict(Counter(x['oracle_decision']['reaction'] for x in refs if next(y for y in ctx if y['context_id']==x['context_id'])['transform'] in ('BASE','SECONDARY'))),'model_execution_authorised':not errors};json.dump(out,open(R/'validation/validation_report.json','w'),indent=2);print(json.dumps(out,indent=2));sys.exit(1 if errors else 0)
