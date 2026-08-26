import csv,json,hashlib,random,itertools
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[1];rng=random.Random(13082650)
ASS=['UNDERSTANDING','ROUTINE','PRACTICAL','ACCESS','CONCERN','REVIEW','UNRESOLVED']
VER=['CONFIRMED','PARTIALLY_CONFIRMED','CONTRADICTED','UNRESOLVED'];REL=['SAME_FUNCTION','DIFFERENT_FUNCTION','UNCERTAIN'];SEC=['ACTIVE','INACTIVE','UNKNOWN'];EVID=['COMPLETE','INCOMPLETE'];REV=['PRESENT','ABSENT'];SUC=['NONE','PROSPECTIVE','VERIFIED','CONTRADICTED']
RX=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE'];CONDS=['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY'];FAMS=['STRUCTURED','CHRONOLOGICAL','CONCISE']
RULES=json.load(open(R/'public/rule_vocabulary.json'))
def oracle(z):
 if z['review_boundary']=='PRESENT':return 'R01_REVIEW_BOUNDARY','ESCALATE_REVIEW'
 if z['evidence_complete']=='INCOMPLETE':return 'R02_EVIDENCE_INCOMPLETE','WAIT_FOR_EVIDENCE'
 if z['current_relation']=='DIFFERENT_FUNCTION':return 'R03_DIFFERENT_FUNCTION','WITHHOLD_ASSUMPTION'
 if z['current_relation']=='UNCERTAIN':return 'R04_UNCERTAIN_FUNCTION','WAIT_FOR_EVIDENCE'
 if z['verification']=='CONTRADICTED':return ('R05_VERIFIED_SUCCESSOR','TAILOR_SUPPORT') if z['successor_state']=='VERIFIED' else ('R06_CONTRADICTED_PREDECESSOR','WITHHOLD_ASSUMPTION')
 if z['verification']=='UNRESOLVED':return 'R07_UNRESOLVED_VERIFICATION','WAIT_FOR_EVIDENCE'
 if z['verification']=='PARTIALLY_CONFIRMED':return 'R08_PARTIALLY_CONFIRMED','TAILOR_SUPPORT'
 if z['secondary_barrier']=='ACTIVE':return 'R09_SECONDARY_BARRIER','TAILOR_SUPPORT'
 return 'R10_CONFIRMED_CONTINUATION','CONTINUE_SUPPORT'
def H(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,rows):
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 with open(p,'w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rows)
# enumerate and select 40 canonical contexts per reaction, balanced rules where possible
pool={r:[] for r in RX}
for vals in itertools.product(VER,REL,SEC,EVID,REV,SUC):
 z=dict(zip(['verification','current_relation','secondary_barrier','evidence_complete','review_boundary','successor_state'],vals));rule,rx=oracle(z);pool[rx].append((z,rule))
selected=[]
for rx in RX:
 candidates=pool[rx][:]
 rng.shuffle(candidates)
 if len(candidates)>=40:
  chosen=candidates[:40]
 else:
  chosen=[rng.choice(candidates) for _ in range(40)]
 selected += [(rx,z,rule) for z,rule in chosen]
# event and rendering helpers
ev=1
def eid():
 global ev
 x=f'EVT-{ev:07d}';ev+=1;return x
def render_event(e,fam):
 if fam=='STRUCTURED':return f"Date {e['time']}; source {e['source']}; observation: {e['fact']}"
 if fam=='CHRONOLOGICAL':return f"On {e['time']}, the {e['source'].replace('_',' ')} recorded that {e['fact'][0].lower()+e['fact'][1:]}"
 return e['fact']
def assumption_text(a):
 return {'UNDERSTANDING':'The plan may not yet be understood consistently.','ROUTINE':'The plan may not yet fit the daily routine.','PRACTICAL':'A practical administration difficulty may be active.','ACCESS':'An access or supply interruption may be active.','CONCERN':'A concern or preference may affect current intention.','REVIEW':'A reported experience may require authorised review.','UNRESOLVED':'No governing support assumption is established.'}[a]
def expected(a):
 return {'UNDERSTANDING':'Teach-back should improve the later account.','ROUTINE':'A routine aid should reduce routine-related omissions.','PRACTICAL':'Practical support should improve later demonstration.','ACCESS':'An access arrangement should improve availability.','CONCERN':'Shared discussion should clarify a preference or review request.','REVIEW':'Authorised review should document the next support step.','UNRESOLVED':'Additional information should distinguish alternatives or leave the state unresolved.'}[a]
latent=[];canonical=[];events=[];contexts=[];refs=[];calls=[];manifest=[];controls=[];rmap=[];calln=1
for i,(rx,z,rule) in enumerate(selected,1):
 cid=f'CAN-{i:04d}';ass=ASS[(i-1)%7];alt=ASS[(i+1)%7];ep=f'EP5-{i:04d}';memory_id=f'MEM5-{i:04d}'
 # facts are observable and do not name oracle state labels
 hist=[{'id':eid(),'time':'2026-06-01','source':'patient_report','fact':f'The formation record contained observations relevant to {ass.lower()}.'},{'id':eid(),'time':'2026-06-08','source':'support_record','fact':'The planned support action was implemented.'}]
 if z['verification']=='CONFIRMED':facts=['The target measure changed in the expected direction during both follow-up contacts.','No same-window observation supported the assessed alternative.']
 elif z['verification']=='PARTIALLY_CONFIRMED':facts=['The target measure changed in the expected direction at follow-up.','A separate same-window observation remained compatible with another support difficulty.']
 elif z['verification']=='CONTRADICTED':facts=['The target measure remained at its pre-support level at both follow-up contacts.','Later observations were compatible with a different support explanation.']
 else:facts=['The record did not establish whether support preceded the later observation.','The available timing did not distinguish the two support explanations.']
 hist += [{'id':eid(),'time':'2026-06-15','source':'patient_report','fact':facts[0]},{'id':eid(),'time':'2026-06-19','source':'patient_report','fact':facts[1]}]
 cur=[]
 if z['review_boundary']=='PRESENT':cf=['A new experience is reported in the current period.','No authorised review record is present, and professional assessment is requested.']
 elif z['evidence_complete']=='INCOMPLETE' or z['current_relation']=='UNCERTAIN':cf=['Current supply and support-action information is present.','The latest account of current plan management predates this period.']
 elif z['current_relation']=='DIFFERENT_FUNCTION':cf=[f'The earlier record concerned {ass.lower()}.',f'The current facts concern {alt.lower()}, with no current observation about {ass.lower()}.']
 elif z['secondary_barrier']=='ACTIVE':cf=['The earlier support difficulty is reported in the current period.','A distinct same-period observation indicates an additional support difficulty.']
 else:cf=['The earlier support difficulty is reported in the current period.','The present source, activity, and time horizon are comparable with the earlier episode.']
 cur=[{'id':eid(),'time':'2026-07-07','source':'patient_report','fact':cf[0]},{'id':eid(),'time':'2026-07-08','source':'support_record','fact':cf[1]}]
 rel={'CONFIRMED':'The target relation changed after support; the assessed alternative was not established.','PARTIALLY_CONFIRMED':'The target relation changed after support while another support difficulty remained active.','CONTRADICTED':'The target relation did not change after support; another explanation was later supported.','UNRESOLVED':'Timing and attribution did not establish whether the expected relation occurred.'}[z['verification']]
 successor_relation=None
 if z['successor_state']!='NONE':
  successor_relation={'statement':'A later alternative relation was observed after its corresponding support action.' if z['successor_state']=='VERIFIED' else 'A later alternative relation was proposed, but its expected consequence has not been established.','provenance_event_ids':[hist[3]['id']],'scope':alt.lower()}
 prospective={'assumption':assumption_text(ass),'expected_consequence':expected(ass),'alternative':alt}
 memory={'memory_id':memory_id,'prospective':prospective,'resolved_relation':{'statement':rel,'constitutive_event_ids':[hist[1]['id'],hist[2]['id']] if z['verification']!='UNRESOLVED' else [],'competing_or_unresolved_event_ids':[hist[3]['id']],'scope':ass.lower(),'limitations':['Availability does not establish medicine use.']},'successor_relation':successor_relation}
 latent.append({'canonical_id':cid,'episode_id':ep,**z,'oracle_reaction':rx,'oracle_rule_id':rule,'assumption':ass,'alternative':alt})
 canonical.append({'canonical_id':cid,'episode_id':ep,'assumption':ass,'memory_id':memory_id,'oracle_reaction':rx,'oracle_rule_id':rule})
 for e in hist+cur:events.append({'canonical_id':cid,**e})
 for fam in FAMS:
  ctx=f'{cid}-{fam[:3]}';rmap.append({'rendered_context_id':ctx,'canonical_id':cid,'render_family':fam})
  h=[{'event_id':e['id'],'event_time':e['time'],'source':e['source'],'content':render_event(e,fam)} for e in hist];c=[{'event_id':e['id'],'event_time':e['time'],'source':e['source'],'content':render_event(e,fam)} for e in cur]
  contexts.append({'context_id':ctx,'canonical_id':cid,'render_family':fam,'oracle_reaction':rx})
  evid={cond:{'historical_groups':[[hist[1]['id'],hist[2]['id']]] if rule not in ['R01_REVIEW_BOUNDARY','R02_EVIDENCE_INCOMPLETE','R03_DIFFERENT_FUNCTION','R04_UNCERTAIN_FUNCTION'] else [],'current_groups':[[e['id'] for e in cur]]} for cond in CONDS}
  ref={'context_id':ctx,'canonical_id':cid,'oracle_decision':{'reaction':rx,'rule_id':rule},'acceptable_evidence':evid};ref['reference_hash']=H(ref);refs.append(ref)
  shared={'world_specification_id':'MSW-0.5','assumption_catalogue_id':'MAC-0.5','verification_policy_id':'MVP-0.5','reaction_policy_id':'MRP-0.5','rule_vocabulary':RULES,'claim_boundary':'Computational correctness only.'}
  base={'shared_world_rules':shared,'current_records':c,'reaction_vocabulary':RX,'required_output':json.load(open(R/'public/response_schema.json'))}
  payloads=[{**base,'condition':'B0_LLM_ALONE','longitudinal_records':h},{**base,'condition':'M0_OPEN_LOOP_MEMORY','longitudinal_records':h,'open_loop_memory':prospective},{**base,'condition':'B1_VERIFIED_MEMORY','longitudinal_records':h,'verified_cognitive_memory':memory}]
  for cond,p in zip(CONDS,payloads):
   call=f'CALL5-{calln:07d}';calln+=1;calls.append({'call_id':call,'context_id':ctx,'canonical_id':cid,'condition':cond,'payload':p});manifest.append({'call_id':call,'context_id':ctx,'canonical_id':cid,'condition':cond})
 # development controls, one per canonical state
 controls += [{'canonical_id':cid,'control':'OUTCOME_ONLY','payload':{'historical_events':[x['id'] for x in hist],'realised_observations':facts}}, {'canonical_id':cid,'control':'SHAM_MEMORY','payload':{'prospective':prospective,'resolved_relation':'No constitutive relation has been established.','matched_structure':True}}, {'canonical_id':cid,'control':'TOKEN_MATCHED_M0','payload':{'prospective':prospective,'neutral_metadata':['source roles preserved','verification window preserved','no resolved consequence supplied']}}]
# split by canonical state, stratified 8 development / 32 reserved per reaction
split=[]
for rx in RX:
 ids=[x['canonical_id'] for x in canonical if x['oracle_reaction']==rx]
 for j,cid in enumerate(ids):split.append({'canonical_id':cid,'split':'DEVELOPMENT' if j<8 else 'RESERVED'})
write(R/'data_v0_5/canonical_contexts.csv' if (R/'data_v0_5').exists() else R/'data/canonical_contexts_v0_5.csv',canonical)
write(R/'data/rendering_map_v0_5.csv',rmap);write(R/'data/split_manifest_v0_5.csv',split);write(R/'data/contexts_v0_5.csv',contexts)
with open(R/'hidden/latent_states_v0_5.jsonl','w') as f:
 for x in latent:f.write(json.dumps(x)+'\n')
with open(R/'hidden/oracle_references_v0_5.jsonl','w') as f:
 for x in refs:f.write(json.dumps(x)+'\n')
with open(R/'data/canonical_events_v0_5.jsonl','w') as f:
 for x in events:f.write(json.dumps(x)+'\n')
with open(R/'prompts/model_calls_v0_5.jsonl','w') as f:
 for x in calls:f.write(json.dumps(x)+'\n')
write(R/'prompts/model_call_manifest_v0_5.csv',manifest)
with open(R/'controls/development_controls_v0_5.jsonl','w') as f:
 for x in controls:f.write(json.dumps(x)+'\n')
(R/'config/generation_schema_v0_5.json').write_text(json.dumps({'version':'0.5','seed':13082650,'canonical_contexts':200,'render_families':FAMS,'rendered_contexts':600,'main_conditions':CONDS,'main_calls':1800,'reaction_balance':40,'development_per_reaction':8,'reserved_per_reaction':32,'controls':'development-only'},indent=2))
print(json.dumps({'canonical':len(canonical),'rendered':len(contexts),'calls':len(calls),'reactions':dict(Counter(x['oracle_reaction'] for x in canonical))},indent=2))
