import csv,json,hashlib,random
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[1];rng=random.Random(13082651)
ASS=['UNDERSTANDING','ROUTINE','PRACTICAL','ACCESS','CONCERN','REVIEW','UNRESOLVED']
RX=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE']
RULE={'CONTINUE_SUPPORT':'R10_CONFIRMED_CONTINUATION','TAILOR_SUPPORT':'R09_SECONDARY_BARRIER','ESCALATE_REVIEW':'R01_REVIEW_BOUNDARY','WITHHOLD_ASSUMPTION':'R03_DIFFERENT_FUNCTION','WAIT_FOR_EVIDENCE':'R02_EVIDENCE_INCOMPLETE'}
CONDS=['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY'];FAMS=['STRUCTURED','CHRONOLOGICAL','CONCISE'];TEMPLATES=['RECURRENCE','ADDITIONAL_OBSERVATION','NEW_EXPERIENCE','SOURCE_CHANGE','TEMPORAL_GAP']
def H(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,rows):
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 with open(p,'w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rows)
ev=1
def eid():
 global ev
 x=f'EVT-{ev:07d}';ev+=1;return x
def render(e,f):
 if f=='STRUCTURED':return f"Date {e['time']}; source {e['source']}; observation: {e['fact']}"
 if f=='CHRONOLOGICAL':return f"On {e['time']}, the {e['source'].replace('_',' ')} recorded that {e['fact'][0].lower()+e['fact'][1:]}"
 return e['fact']
def ass_text(a):return {'UNDERSTANDING':'The plan may not yet be understood consistently.','ROUTINE':'The plan may not yet fit daily routine.','PRACTICAL':'A practical administration difficulty may be active.','ACCESS':'An access or supply interruption may be active.','CONCERN':'A concern may affect current intention.','REVIEW':'A reported experience may require authorised review.','UNRESOLVED':'No governing support assumption is established.'}[a]
def expected(a):return {'UNDERSTANDING':'Teach-back should improve the later account.','ROUTINE':'A routine aid should reduce routine-related omissions.','PRACTICAL':'Practical support should improve later demonstration.','ACCESS':'An access arrangement should improve availability.','CONCERN':'Shared discussion should clarify a preference or review request.','REVIEW':'Authorised review should document the next support step.','UNRESOLVED':'Additional information should distinguish alternatives or leave the state unresolved.'}[a]
# 40 reusable memories, each paired with all five reactions. This makes memory-only non-predictive.
memories=[];events=[]
for m in range(40):
 mid=f'MEM51-{m+1:04d}';ass=ASS[m%7];alt=ASS[(m+2)%7];verification=['CONFIRMED','PARTIALLY_CONFIRMED','CONTRADICTED','UNRESOLVED'][m%4]
 h=[{'id':eid(),'time':'2026-08-01','source':'patient_report','fact':'The formation record contained two observations relevant to the represented support relation.'},{'id':eid(),'time':'2026-08-08','source':'support_record','fact':'The planned support action was implemented during the declared verification window.'}]
 facts={
 'CONFIRMED':['The target measure changed in the expected direction at two subsequent contacts.','The assessed alternative was not observed during the same window.'],
 'PARTIALLY_CONFIRMED':['The target measure changed in the expected direction at follow-up.','A second support difficulty remained observable during the same window.'],
 'CONTRADICTED':['The target measure remained at its earlier level at two subsequent contacts.','A different support relation was later observed.'],
 'UNRESOLVED':['The order between support and follow-up observation was not established.','The available timing did not distinguish two support relations.']}[verification]
 h += [{'id':eid(),'time':'2026-08-15','source':'patient_report','fact':facts[0]},{'id':eid(),'time':'2026-08-20','source':'patient_report','fact':facts[1]}]
 # Episode-specific comparison guide. Raw history contains the facts; B1 preserves their resolved relation.
 meanings={
 'CONTINUE_SUPPORT':'The current relation is comparable and no additional barrier is active.',
 'TAILOR_SUPPORT':'The current relation is comparable and an additional barrier remains active.',
 'ESCALATE_REVIEW':'The current report matches the represented authorised-review boundary and no completed current review is recorded.',
 'WITHHOLD_ASSUMPTION':'The current relation belongs to a different support function from the verified scope.',
 'WAIT_FOR_EVIDENCE':'A comparison-critical current field is absent, so applicability cannot be established.'}
 codes=['relation-alpha','relation-beta','relation-gamma','relation-delta','relation-epsilon'];rng.shuffle(codes)
 reaction_to_code=dict(zip(RX,codes));guide={reaction_to_code[r]:meanings[r] for r in RX}
 for j,(code,meaning) in enumerate(guide.items()):h.append({'id':eid(),'time':f'2026-08-{21+j:02d}','source':'support_record','fact':f'For this episode, comparison marker {code} records: {meaning}'})
 rel={'CONFIRMED':'The target relation changed after support and the assessed alternative was not established.','PARTIALLY_CONFIRMED':'The target relation changed after support while a second support difficulty remained.','CONTRADICTED':'The target relation did not change after support and another relation was later observed.','UNRESOLVED':'Timing did not establish whether the expected relation occurred.'}[verification]
 prospective={'assumption':ass_text(ass),'expected_consequence':expected(ass),'alternative':alt}
 memory={'memory_id':mid,'prospective':prospective,'resolved_relation':{'statement':rel,'constitutive_event_ids':[h[1]['id'],h[2]['id']] if verification!='UNRESOLVED' else [],'competing_or_unresolved_event_ids':[h[3]['id']],'scope':ass.lower(),'limitations':['Availability does not establish medicine use.']},'comparison_guide':guide,'successor_relation':{'statement':'A later alternative relation was observed; applicability must be established from current evidence.','provenance_event_ids':[h[3]['id']],'scope':alt.lower()} if verification=='CONTRADICTED' else None}
 memories.append({'memory_id':mid,'assumption':ass,'alternative':alt,'verification':verification,'historical_events':h,'prospective':prospective,'memory':memory,'reaction_to_code':reaction_to_code})
 for e in h:events.append({'memory_id':mid,**e})
# Current template facts are reaction-balanced via Latin square. Each template occurs 8 times per reaction.
TFACT={
'RECURRENCE':['A previously represented difficulty is mentioned in the current record.','The record also contains a current observation from another support source.'],
'ADDITIONAL_OBSERVATION':['Two current support observations are present in the same period.','One observation uses terminology also found in earlier records.'],
'NEW_EXPERIENCE':['A new experience is described during the current period.','The record includes a request for clarification and a status entry from another source.'],
'SOURCE_CHANGE':['The current record uses a source different from the earlier episode.','The observed activity has both a similarity and a difference from the historical record.'],
'TEMPORAL_GAP':['Current-period administrative information is available.','The latest patient account and the latest support record cover different time points.']}
# Hidden interpretation links generic facts to memory; not rendered literally.
HIDDEN_BY_RX={
'CONTINUE_SUPPORT':{'relation':'SAME_FUNCTION','evidence':'COMPLETE','review':'RESOLVED','secondary':'INACTIVE'},
'TAILOR_SUPPORT':{'relation':'SAME_FUNCTION','evidence':'COMPLETE','review':'RESOLVED','secondary':'ACTIVE'},
'ESCALATE_REVIEW':{'relation':'SAME_FUNCTION','evidence':'COMPLETE','review':'PRESENT_UNRESOLVED','secondary':'UNKNOWN'},
'WITHHOLD_ASSUMPTION':{'relation':'DIFFERENT_FUNCTION','evidence':'COMPLETE','review':'RESOLVED','secondary':'INACTIVE'},
'WAIT_FOR_EVIDENCE':{'relation':'UNCERTAIN','evidence':'INCOMPLETE','review':'UNKNOWN','secondary':'UNKNOWN'}}
canonical=[];current_events=[];contexts=[];refs=[];calls=[];manifest=[];controls=[];rmap=[];calln=1
for mi,mem in enumerate(memories):
 for ri,rx in enumerate(RX):
  cid=f'CAN51-{mi*5+ri+1:04d}';template=TEMPLATES[(mi+ri)%5];hidden={**HIDDEN_BY_RX[rx],'memory_id':mem['memory_id'],'template_family':template,'oracle_reaction':rx,'oracle_rule_id':RULE[rx]}
  # Same template facts across reactions; add neutral, reaction-balanced attributes whose interpretation requires memory.
  facts=TFACT[template]
  cur=[{'id':eid(),'time':'2026-09-10','source':'patient_report','fact':facts[0]},{'id':eid(),'time':'2026-09-11','source':'support_record','fact':facts[1]}]
  # opaque relational observations, equally distributed; memory/current combination is needed
  code=mem['reaction_to_code'][rx]
  cur.append({'id':eid(),'time':'2026-09-12','source':'administrative_record','fact':f'The current comparison marker is {code}; its meaning depends on the historical scope and provenance supplied for this episode.'})
  for e in cur:current_events.append({'canonical_id':cid,**e})
  canonical.append({'canonical_id':cid,'memory_id':mem['memory_id'],'template_family':template,'oracle_reaction':rx,'oracle_rule_id':RULE[rx]})
  for fam in FAMS:
   ctx=f'{cid}-{fam[:3]}';rmap.append({'context_id':ctx,'canonical_id':cid,'memory_id':mem['memory_id'],'render_family':fam});h=[{'event_id':e['id'],'event_time':e['time'],'source':e['source'],'content':render(e,fam)} for e in mem['historical_events']];c=[{'event_id':e['id'],'event_time':e['time'],'source':e['source'],'content':render(e,fam)} for e in cur]
   contexts.append({'context_id':ctx,'canonical_id':cid,'memory_id':mem['memory_id'],'render_family':fam,'template_family':template,'oracle_reaction':rx})
   # evidence groups require historical and current for all primary cases
   evid={cond:{'historical_groups':[[mem['historical_events'][1]['id'],mem['historical_events'][2]['id']]],'current_groups':[[e['id'] for e in cur]]} for cond in CONDS}
   ref={'context_id':ctx,'canonical_id':cid,'memory_id':mem['memory_id'],'hidden_current_interpretation':hidden,'oracle_decision':{'reaction':rx,'rule_id':RULE[rx]},'acceptable_evidence':evid};ref['reference_hash']=H(ref);refs.append(ref)
   shared={'world_specification_id':'MSW-0.5.1','reaction_policy_id':'MRP-0.5.1','rule_vocabulary':json.load(open(R/'public/rule_vocabulary.json')),'claim_boundary':'Computational correctness only.','comparison_marker_note':'Comparison markers are arbitrary relation identifiers. They have no reaction meaning without episode history.'}
   base={'shared_world_rules':shared,'reaction_vocabulary':RX,'response_schema':json.load(open(R/'public/response_schema.json')),'current_records':c}
   payloads=[{**base,'condition':'B0_LLM_ALONE','longitudinal_records':h},{**base,'condition':'M0_OPEN_LOOP_MEMORY','longitudinal_records':h,'open_loop_memory':mem['prospective']},{**base,'condition':'B1_VERIFIED_MEMORY','longitudinal_records':h,'verified_cognitive_memory':mem['memory']}]
   for cond,p in zip(CONDS,payloads):
    call=f'CALL51-{calln:07d}';calln+=1;calls.append({'call_id':call,'context_id':ctx,'canonical_id':cid,'memory_id':mem['memory_id'],'condition':cond,'payload':p});manifest.append({'call_id':call,'context_id':ctx,'canonical_id':cid,'memory_id':mem['memory_id'],'condition':cond})
  controls += [{'canonical_id':cid,'control':'CURRENT_ONLY','payload':{'current_event_ids':[e['id'] for e in cur]}},{'canonical_id':cid,'control':'MEMORY_ONLY','payload':mem['memory']},{'canonical_id':cid,'control':'ASSUMPTION_ONLY','payload':mem['prospective']}]
# split by memory, not context, to prevent shared-memory leakage: 8 dev memories -> 40 canonical, 32 reserved -> 160
split=[{'memory_id':m['memory_id'],'split':'DEVELOPMENT' if i<8 else 'RESERVED'} for i,m in enumerate(memories)]
write(R/'data_v0_5_1/canonical_contexts.csv',canonical);write(R/'data_v0_5_1/rendering_map.csv',rmap);write(R/'data_v0_5_1/contexts.csv',contexts);write(R/'data_v0_5_1/split_manifest.csv',split);write(R/'data_v0_5_1/memories.csv',[{'memory_id':m['memory_id'],'assumption':m['assumption'],'verification':m['verification'],'memory_json':json.dumps(m['memory'],separators=(',',':'))} for m in memories])
with open(R/'data_v0_5_1/historical_events.jsonl','w') as f:
 for x in events:f.write(json.dumps(x)+'\n')
with open(R/'data_v0_5_1/current_events.jsonl','w') as f:
 for x in current_events:f.write(json.dumps(x)+'\n')
with open(R/'hidden/oracle_references_v0_5_1.jsonl','w') as f:
 for x in refs:f.write(json.dumps(x)+'\n')
with open(R/'prompts/model_calls_v0_5_1.jsonl','w') as f:
 for x in calls:f.write(json.dumps(x)+'\n')
write(R/'prompts/model_call_manifest_v0_5_1.csv',manifest)
with open(R/'controls/baseline_inputs_v0_5_1.jsonl','w') as f:
 for x in controls:f.write(json.dumps(x)+'\n')
(R/'config/generation_schema_v0_5_1.json').write_text(json.dumps({'version':'0.5.1','seed':13082651,'memories':40,'contexts_per_memory':5,'canonical_contexts':200,'reaction_balance':40,'template_reaction_matrix':'8 per cell','render_families':FAMS,'rendered_contexts':600,'calls':1800,'split_unit':'memory','development_memories':8,'reserved_memories':32},indent=2))
print(json.dumps({'memories':40,'canonical':len(canonical),'rendered':len(contexts),'calls':len(calls),'reactions':dict(Counter(x['oracle_reaction'] for x in canonical)),'templates':dict(Counter(x['template_family'] for x in canonical))},indent=2))
