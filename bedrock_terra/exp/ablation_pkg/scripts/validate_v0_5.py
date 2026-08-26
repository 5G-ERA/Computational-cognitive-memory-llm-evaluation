import csv,json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
R=Path(__file__).resolve().parents[1];read=lambda p:list(csv.DictReader(open(R/p)))
canon=read('data_v0_5/canonical_contexts.csv');rmap=read('data/rendering_map_v0_5.csv');spl=read('data/split_manifest_v0_5.csv');ctx=read('data/contexts_v0_5.csv');calls=[json.loads(x) for x in open(R/'prompts/model_calls_v0_5.jsonl')];refs=[json.loads(x) for x in open(R/'hidden/oracle_references_v0_5.jsonl')];controls=[json.loads(x) for x in open(R/'controls/development_controls_v0_5.jsonl')]
checks={'canonical_200':len(canon)==200,'balanced_reactions':set(Counter(x['oracle_reaction'] for x in canon).values())=={40},'rendered_600':len(ctx)==600 and len(rmap)==600,'three_renderings_each':set(Counter(x['canonical_id'] for x in rmap).values())=={3},'calls_1800':len(calls)==1800,'three_conditions_each':set(Counter(x['context_id'] for x in calls).values())=={3},'split_40_160':Counter(x['split'] for x in spl)=={'DEVELOPMENT':40,'RESERVED':160},'controls_600':len(controls)==600,'refs_600':len(refs)==600}
# rendering semantic identity and condition parity
by=defaultdict(dict)
for x in calls:by[x['context_id']][x['condition']]=x['payload']
parity=hier=True
for d in by.values():
 b,m,v=d['B0_LLM_ALONE'],d['M0_OPEN_LOOP_MEMORY'],d['B1_VERIFIED_MEMORY'];parity &= b['longitudinal_records']==m['longitudinal_records']==v['longitudinal_records'] and b['current_records']==m['current_records']==v['current_records'];hier &= 'open_loop_memory' not in b and 'open_loop_memory' in m and 'verified_cognitive_memory' not in m and 'verified_cognitive_memory' in v
checks['condition_parity']=parity;checks['condition_hierarchy']=hier
# same oracle across renderings
rm=defaultdict(set)
for x in refs:rm[x['canonical_id']].add((x['oracle_decision']['reaction'],x['oracle_decision']['rule_id']))
checks['rendering_oracle_equivalence']=all(len(v)==1 for v in rm.values())
# no reaction token in episode-specific records/memory
rx=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE'];leak=[]
for x in calls:
 s=json.dumps({k:v for k,v in x['payload'].items() if k not in ('reaction_vocabulary','shared_world_rules','required_output')}).upper()
 if any(re.search(r'\b'+t+r'\b',s) for t in rx):leak.append(x['call_id'])
checks['no_episode_reaction_leak']=not leak
errors=[k for k,v in checks.items() if not v];out={'status':'PASS' if not errors else 'FAIL','errors':errors,'checks':checks,'reaction_distribution':dict(Counter(x['oracle_reaction'] for x in canon)),'render_families':dict(Counter(x['render_family'] for x in ctx)),'note':'Development package. Challenge baselines and external API QA must pass before reserved execution.'};json.dump(out,open(R/'validation/validation_report_v0_5.json','w'),indent=2);print(json.dumps(out,indent=2));sys.exit(1 if errors else 0)
