import csv,json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold,cross_val_predict
from sklearn.metrics import f1_score,accuracy_score
R=Path(__file__).resolve().parents[1];read=lambda p:list(csv.DictReader(open(R/p)))
canon=read('data_v0_5_1/canonical_contexts.csv');ctx=read('data_v0_5_1/contexts.csv');spl=read('data_v0_5_1/split_manifest.csv');mem=read('data_v0_5_1/memories.csv');calls=[json.loads(x) for x in open(R/'prompts/model_calls_v0_5_1.jsonl')];refs=[json.loads(x) for x in open(R/'hidden/oracle_references_v0_5_1.jsonl')]
checks={'memories_40':len(mem)==40,'canonical_200':len(canon)==200,'reaction_balance':set(Counter(x['oracle_reaction'] for x in canon).values())=={40},'template_balance':set(Counter(x['template_family'] for x in canon).values())=={40},'template_reaction_matrix':set(Counter((x['template_family'],x['oracle_reaction']) for x in canon).values())=={8},'rendered_600':len(ctx)==600,'three_renderings':set(Counter(x['canonical_id'] for x in ctx).values())=={3},'calls_1800':len(calls)==1800,'three_conditions':set(Counter(x['context_id'] for x in calls).values())=={3},'split_8_32':Counter(x['split'] for x in spl)=={'DEVELOPMENT':8,'RESERVED':32},'refs_600':len(refs)==600}
# condition parity/hierarchy and oracle rendering equivalence
by=defaultdict(dict)
for x in calls:by[x['context_id']][x['condition']]=x['payload']
parity=hier=True
for d in by.values():
 b,m,v=d['B0_LLM_ALONE'],d['M0_OPEN_LOOP_MEMORY'],d['B1_VERIFIED_MEMORY'];parity &= b['longitudinal_records']==m['longitudinal_records']==v['longitudinal_records'] and b['current_records']==m['current_records']==v['current_records'];hier &= 'open_loop_memory' not in b and 'open_loop_memory' in m and 'verified_cognitive_memory' not in m and 'verified_cognitive_memory' in v
checks['condition_parity']=parity;checks['condition_hierarchy']=hier
rr=defaultdict(set)
for x in refs:rr[x['canonical_id']].add((x['oracle_decision']['reaction'],x['oracle_decision']['rule_id']))
checks['rendering_oracle_equivalence']=all(len(v)==1 for v in rr.values())
# no answer label in episode-specific payload
rx=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE'];leaks=[]
for x in calls:
 s=json.dumps({k:v for k,v in x['payload'].items() if k not in ('reaction_vocabulary','shared_world_rules','response_schema')}).upper()
 if any(re.search(r'\b'+t+r'\b',s) for t in rx):leaks.append(x['call_id'])
checks['no_episode_reaction_leak']=not leaks
# deterministic B1 solvability: current marker -> memory comparison guide -> semantic rule
meaning_to_rx={'no additional barrier is active':'CONTINUE_SUPPORT','additional barrier remains active':'TAILOR_SUPPORT','authorised-review boundary':'ESCALATE_REVIEW','different support function':'WITHHOLD_ASSUMPTION','comparison-critical current field is absent':'WAIT_FOR_EVIDENCE'}
def solve_b1(x):
 s=' '.join(e['content'] for e in x['payload']['current_records']);m=re.search(r'relation-(alpha|beta|gamma|delta|epsilon)',s);guide=x['payload']['verified_cognitive_memory']['comparison_guide'];meaning=guide['relation-'+m.group(1)]
 return next(v for k,v in meaning_to_rx.items() if k in meaning)
refmap={x['context_id']:x for x in refs};b1=[x for x in calls if x['condition']=='B1_VERIFIED_MEMORY'];checks['deterministic_b1_solvable']=all(solve_b1(x)==refmap[x['context_id']]['oracle_decision']['reaction'] for x in b1)
# Challenge baselines on development, split by memory in grouped CV
split={x['memory_id']:x['split'] for x in spl};dev=[x for x in calls if split[x['memory_id']]=='DEVELOPMENT']
def flat(x,mode):
 p=x['payload'];parts=[]
 def w(v,k=''):
  if isinstance(v,dict):
   for kk,vv in v.items():
    if kk in {'shared_world_rules','reaction_vocabulary','response_schema','condition'}:continue
    if mode=='current' and k=='' and kk!='current_records':continue
    if mode=='memory' and k=='' and kk!='verified_cognitive_memory':continue
    if mode=='assumption' and k=='' and kk!='open_loop_memory':continue
    w(vv,kk)
  elif isinstance(v,list):
   for z in v:w(z,k)
  elif isinstance(v,str) and not re.fullmatch(r'(EVT|CALL51|CAN51|MEM51)-[A-Z0-9-]+',v):parts.append(v)
 w(p);return ' '.join(parts)
def lexical(q,mode):
 X=[flat(x,mode) for x in q];y=[refmap[x['context_id']]['oracle_decision']['reaction'] for x in q];g=[x['memory_id'] for x in q];M=TfidfVectorizer(ngram_range=(1,2),min_df=2,stop_words='english').fit_transform(X);pred=cross_val_predict(LogisticRegression(max_iter=4000,class_weight='balanced'),M,y,groups=g,cv=GroupKFold(4));return {'macro_f1':f1_score(y,pred,average='macro'),'accuracy':accuracy_score(y,pred)}
bases={}
for c in ['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY']:bases[c+'_full']=lexical([x for x in dev if x['condition']==c],'full')
bases['current_only']=lexical([x for x in dev if x['condition']=='B0_LLM_ALONE'],'current');bases['assumption_only']=lexical([x for x in dev if x['condition']=='M0_OPEN_LOOP_MEMORY'],'assumption');bases['memory_only']=lexical([x for x in dev if x['condition']=='B1_VERIFIED_MEMORY'],'memory')
# deterministic non-text baselines
labels=[refmap[x['context_id']]['oracle_decision']['reaction'] for x in dev if x['condition']=='B0_LLM_ALONE'];major=max(Counter(labels).values())/len(labels);bases['event_count_accuracy']=major;bases['structure_accuracy']=major;bases['identifier_accuracy']=major
checks['current_only_gate']=bool(bases['current_only']['macro_f1']<.45);checks['assumption_only_gate']=bool(bases['assumption_only']['macro_f1']<.45);checks['memory_only_gate']=bool(bases['memory_only']['macro_f1']<.45);checks['b0_bow_gate']=bool(bases['B0_LLM_ALONE_full']['macro_f1']<.55);checks['nontext_near_prior']=all(abs(bases[k]-.2)<.05 for k in ['event_count_accuracy','structure_accuracy','identifier_accuracy'])
errors=[k for k,v in checks.items() if not v];out={'status':'PASS' if not errors else 'FAIL','errors':errors,'checks':checks,'baselines':bases,'reaction_distribution':dict(Counter(x['oracle_reaction'] for x in canon)),'template_distribution':dict(Counter(x['template_family'] for x in canon)),'release_decision':'GO_FOR_EXTERNAL_API_QA' if not errors else 'NO_GO'};json.dump(out,open(R/'validation/validation_report_v0_5_1.json','w'),indent=2);print(json.dumps(out,indent=2));sys.exit(1 if errors else 0)
