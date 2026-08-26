import csv,json,hashlib,random,itertools
from pathlib import Path
from datetime import date,timedelta
from collections import Counter
R=Path(__file__).resolve().parents[1]; SEED=13082642; rng=random.Random(SEED)
ASS={
'UNDERSTANDING':{'q':'Does the person understand the agreed plan?','s':'The leading assumption is that the agreed plan is not yet understood consistently or accessibly.','k':'Accessible explanation and teach-back should improve the later account of the plan.','formation':['Two different accounts of the agreed timing were recorded.','Accessible information was requested.'],'action':'An accessible explanation and teach-back check were completed.','measure':'At follow-up, the person described the agreed timing correctly at both contacts.'},
'ROUTINE':{'q':'Can the plan fit daily routine?','s':'The leading assumption is that the agreed plan has not been integrated reliably into daily routine.','k':'An implemented routine aid should reduce routine-related missed-use reports.','formation':['Two missed occasions followed changes in the evening schedule.','The agreed instructions were described consistently.'],'action':'The agreed reminder was activated and linked to the evening routine.','measure':'During fourteen days, one missed occasion was reported after an unexpected schedule change.'},
'PRACTICAL':{'q':'Can the plan be carried out practically?','s':'The leading assumption is that a practical administration difficulty prevents reliable implementation.','k':'Practical support should improve later demonstration or reported manageability.','formation':['One administration step was not completed during demonstration.','The instructions were otherwise described consistently.'],'action':'Practical support and a repeat demonstration were completed.','measure':'At follow-up, the previously missed administration step was completed correctly.'},
'ACCESS':{'q':'Is the medicine or support available?','s':'The leading assumption is that access, supply, collection, or delivery interrupts availability.','k':'An implemented access arrangement should improve later availability.','formation':['The planned collection was delayed because the regular arrangement was unavailable.','The person stated an intention to follow the agreed plan.'],'action':'A delivery arrangement was activated for the next supply.','measure':'The next supply became available within the planned collection window.'},
'CONCERN':{'q':'Does the person currently intend to follow the plan?','s':'The leading assumption is that a stated concern or preference affects current intention.','k':'Shared discussion should clarify the concern and record a decision or review request.','formation':['The person questioned the expected benefit.','The agreed instructions were described accurately.'],'action':'A shared discussion of concerns and preferences was completed.','measure':'The follow-up record contained a stated preference and a request for further review.'},
'REVIEW':{'q':'Is authorised healthcare review required?','s':'The leading assumption is that a reported experience requires authorised healthcare review.','k':'Authorised review should clarify the concern and document the next step.','formation':['A new experience was reported after the support episode began.','The person requested professional assessment before deciding how to proceed.'],'action':'An authorised healthcare review was completed.','measure':'The authorised review record documented the concern and the next support step without assigning medicine causality.'},
'UNRESOLVED':{'q':'Is there enough evidence to select a governing assumption?','s':'The available evidence does not yet establish a governing support assumption.','k':'Additional information should distinguish credible alternatives or the episode should remain unresolved.','formation':['The patient account was incomplete.','More than one support explanation remained plausible.'],'action':'A further information-gathering contact was arranged.','measure':'The follow-up record still lacked the timing needed to distinguish the two explanations.'}}
VER=['CONFIRMED','PARTIALLY_CONFIRMED','CONTRADICTED','UNRESOLVED']
RX=['CONTINUE_SUPPORT','TAILOR_SUPPORT','ESCALATE_REVIEW','WITHHOLD_ASSUMPTION','WAIT_FOR_EVIDENCE']
RULES={
'R01_REVIEW_BOUNDARY':'ESCALATE_REVIEW','R02_EVIDENCE_INCOMPLETE':'WAIT_FOR_EVIDENCE','R03_DIFFERENT_FUNCTION':'WITHHOLD_ASSUMPTION','R04_UNCERTAIN_FUNCTION':'WAIT_FOR_EVIDENCE','R05_VERIFIED_SUCCESSOR':'TAILOR_SUPPORT','R06_CONTRADICTED_PREDECESSOR':'WITHHOLD_ASSUMPTION','R07_UNRESOLVED_VERIFICATION':'WAIT_FOR_EVIDENCE','R08_PARTIALLY_CONFIRMED':'TAILOR_SUPPORT','R09_SECONDARY_BARRIER':'TAILOR_SUPPORT','R10_CONFIRMED_CONTINUATION':'CONTINUE_SUPPORT'}
CONDS=['B0_LLM_ALONE','M0_OPEN_LOOP_MEMORY','B1_VERIFIED_MEMORY']
def H(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,rows):
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rows)
def oracle(z):
 if z['review_boundary']=='PRESENT':return 'R01_REVIEW_BOUNDARY',RULES['R01_REVIEW_BOUNDARY']
 if z['evidence_complete']=='INCOMPLETE':return 'R02_EVIDENCE_INCOMPLETE',RULES['R02_EVIDENCE_INCOMPLETE']
 if z['current_relation']=='DIFFERENT_FUNCTION':return 'R03_DIFFERENT_FUNCTION',RULES['R03_DIFFERENT_FUNCTION']
 if z['current_relation']=='UNCERTAIN':return 'R04_UNCERTAIN_FUNCTION',RULES['R04_UNCERTAIN_FUNCTION']
 if z['verification']=='CONTRADICTED':
  k='R05_VERIFIED_SUCCESSOR' if z['successor_state']=='VERIFIED' else 'R06_CONTRADICTED_PREDECESSOR';return k,RULES[k]
 if z['verification']=='UNRESOLVED':return 'R07_UNRESOLVED_VERIFICATION',RULES['R07_UNRESOLVED_VERIFICATION']
 if z['verification']=='PARTIALLY_CONFIRMED':return 'R08_PARTIALLY_CONFIRMED',RULES['R08_PARTIALLY_CONFIRMED']
 if z['secondary_barrier']=='ACTIVE':return 'R09_SECONDARY_BARRIER',RULES['R09_SECONDARY_BARRIER']
 return 'R10_CONFIRMED_CONTINUATION',RULES['R10_CONFIRMED_CONTINUATION']
# public resources
world={'world_id':'MSW-0.4.2','purpose':'Recover oracle-defined reactions in a disclosed synthetic medicines-support world.','claim_boundary':'Computational correctness only; not medical correctness.','conditions':{'B0_LLM_ALONE':'Raw longitudinal evidence.','M0_OPEN_LOOP_MEMORY':'B0 plus prospective assumption and expected consequence.','B1_VERIFIED_MEMORY':'M0 plus verified relational memory.'}}
(R/'public/world_specification.json').write_text(json.dumps(world,indent=2))
write(R/'public/assumption_catalogue.csv',[{'code':k,'intuitive_question':v['q'],'statement':v['s'],'expected_consequence':v['k'],'prohibited_inference':'No diagnosis, prescribing, treatment change, coercion, or inference that supply proves use.','source_url':'https://www.nice.org.uk/guidance/cg76/chapter/Recommendations'} for k,v in ASS.items()])
verification_rules={'CONFIRMED':'Support was implemented; the predicted observation occurred; timing was sufficient; no better competing explanation was established.','PARTIALLY_CONFIRMED':'The predicted observation occurred, while another support barrier remained active.','CONTRADICTED':'Support was implemented, but the predicted observation did not occur and direct continuation was not warranted.','UNRESOLVED':'Implementation, timing, attribution, or completeness was insufficient.'}
(R/'public/verification_rules.json').write_text(json.dumps(verification_rules,indent=2))
rule_vocab={k:{'reaction':v,'description':{'R01_REVIEW_BOUNDARY':'A current report requires authorised healthcare review.','R02_EVIDENCE_INCOMPLETE':'Comparison-critical current evidence is incomplete.','R03_DIFFERENT_FUNCTION':'The current issue belongs to a different support function.','R04_UNCERTAIN_FUNCTION':'The current functional relation cannot be established.','R05_VERIFIED_SUCCESSOR':'A verified successor governs after predecessor contradiction.','R06_CONTRADICTED_PREDECESSOR':'The contradicted predecessor cannot govern and no verified successor applies.','R07_UNRESOLVED_VERIFICATION':'The historical assumption remains unresolved.','R08_PARTIALLY_CONFIRMED':'The historical relation remains useful with qualification.','R09_SECONDARY_BARRIER':'A secondary barrier is currently active.','R10_CONFIRMED_CONTINUATION':'A confirmed historical relation remains comparable.'}[k]} for k,v in RULES.items()}
(R/'public/rule_vocabulary.json').write_text(json.dumps(rule_vocab,indent=2))
(R/'public/reaction_policy.json').write_text(json.dumps({'policy_id':'MRP-0.4.2','precedence':list(RULES),'rule_vocabulary':rule_vocab},indent=2))
(R/'public/observation_dictionary.json').write_text(json.dumps({'patient_report':'May report understanding, routine, preference, experience, or current management; does not establish clinical causality.','support_record':'May establish whether a support action was implemented.','administrative_record':'May establish availability or attendance; does not establish medicine use.','authorised_review':'May report review status and the documented next support step.'},indent=2))
response_schema={'type':'object','required':['reaction','rule_id','decisive_event_ids','reason'],'properties':{'reaction':{'type':'string','enum':RX},'rule_id':{'type':'string','enum':list(RULES)},'decisive_event_ids':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string','pattern':'^EVT-[0-9]{7}$'}},'reason':{'type':'string','minLength':1,'maxLength':600}},'additionalProperties':False}
(R/'public/response_schema.json').write_text(json.dumps(response_schema,indent=2))
shared={'world':world,'assumptions':{k:{'question':v['q'],'statement':v['s'],'expected_consequence':v['k']} for k,v in ASS.items()},'verification_rules':verification_rules,'reaction_policy':{'precedence':list(RULES),'rules':rule_vocab},'observation_dictionary':json.loads((R/'public/observation_dictionary.json').read_text())}
# data
episodes=[];hist_events=[];memories=[];contexts=[];cur_events=[];latent=[];refs=[];flags=[];calls=[];manifest=[];evn=1;epn=1;ctxn=1;calln=1;base=date(2026,5,4)
def eid():
 global evn
 x=f'EVT-{evn:07d}';evn+=1;return x
for ai,(ac,a) in enumerate(ASS.items()):
 for vi,ver in enumerate(VER):
  ep=f'EP-{epn:04d}';pat=f'SYN-{epn:04d}';epn+=1;ft=base+timedelta(days=(epn-2)*9);alt=list(ASS)[(ai+vi+1)%len(ASS)]
  successor='VERIFIED' if ver=='CONTRADICTED' and ai%2==0 else ('PROSPECTIVE' if ver=='CONTRADICTED' else 'NONE')
  fe=[]
  for i,t in enumerate(a['formation']):fe.append({'episode_id':ep,'event_id':eid(),'patient_id':pat,'event_time':(ft-timedelta(days=2-i)).isoformat(),'source':'patient_report','role':'formation_observation','content':t})
  # Raw observations. Wording does not state verification labels.
  if ver=='CONFIRMED': target=a['measure']; altobs=f'No observation supporting the alternative {alt.lower()} explanation was recorded in the same window.'
  elif ver=='PARTIALLY_CONFIRMED': target=a['measure']; altobs=f'A separate current-period observation remained compatible with the {alt.lower()} explanation.'
  elif ver=='CONTRADICTED': target='At both follow-up contacts, the original difficulty remained at the same recorded level as before support.'; altobs=f'Two later observations were consistent with the {alt.lower()} explanation.'
  else: target='The follow-up record did not establish whether the support action preceded the later observation.'; altobs=f'The available records could not distinguish the {ac.lower()} and {alt.lower()} explanations.'
  rr=[]
  for i,(src,role,t) in enumerate([('support_record','support_action',a['action']),('patient_report','target_measure',target),('patient_report','alternative_measure',altobs),('administrative_record','limited_evidence','A supply or attendance entry was available, but it did not establish medicine use.'),('patient_report','attribution_limit','A related note lacked enough timing detail to establish attribution on its own.')]):rr.append({'episode_id':ep,'event_id':eid(),'patient_id':pat,'event_time':(ft+timedelta(days=7+i*4)).isoformat(),'source':src,'role':role,'content':t})
  hist_events+=fe+rr
  prospective={'assumption':a['s'],'expected_consequence':a['k'],'alternatives':[alt],'verification_window_days':28,'formation_event_ids':[x['event_id'] for x in fe]}
  rel_statement={'CONFIRMED':'The observed target relation changed after the support action, and the assessed alternative was not established.','PARTIALLY_CONFIRMED':f'The observed target relation changed after support, while evidence compatible with {alt.lower()} remained active.','CONTRADICTED':f'The observed target relation did not change after support, while later observations supported {alt.lower()} as a successor candidate.','UNRESOLVED':'The available timing and attribution were insufficient to determine whether the expected relation occurred.'}[ver]
  verified={'resolved_relation':rel_statement,'constitutive_event_ids':[rr[0]['event_id'],rr[1]['event_id']] if ver!='UNRESOLVED' else [],'competing_or_unresolved_event_ids':[rr[2]['event_id']],'scope':{'historical_function':ac.lower(),'current_comparability_required':True},'limitations':['Supply or attendance does not establish medicine use.','No treatment-change authority.'],'internal_verification':ver}
  memory={'memory_id':f'MEM-{ep[3:]}','prospective':prospective,'verified_relation':{k:v for k,v in verified.items() if k!='internal_verification'},'successor':{'code':alt if successor!='NONE' else '','state':successor}}
  memories.append({'episode_id':ep,'memory_id':memory['memory_id'],'open_loop_json':json.dumps(prospective,separators=(',',':')),'closed_loop_json':json.dumps(memory,separators=(',',':')),'memory_hash':H(memory)})
  episodes.append({'episode_id':ep,'patient_id':pat,'assumption':ac,'verification':ver,'successor_state':successor,'memory_hash':H(memory)})
  latent.append({'episode_id':ep,'primary_assumption':ac,'alternative_assumption':alt,'verification':ver,'successor_state':successor})
  # Each episode produces five states; only BASE/SECONDARY/MEMORY_GAP primary candidates.
  states=[
   ('BASE',{'current_relation':'SAME_FUNCTION','secondary_barrier':'INACTIVE','evidence_complete':'COMPLETE','review_boundary':'ABSENT'}),
   ('SECONDARY',{'current_relation':'SAME_FUNCTION','secondary_barrier':'ACTIVE','evidence_complete':'COMPLETE','review_boundary':'ABSENT'}),
   ('DIFFERENT',{'current_relation':'DIFFERENT_FUNCTION','secondary_barrier':'INACTIVE','evidence_complete':'COMPLETE','review_boundary':'ABSENT'}),
   ('MISSING',{'current_relation':'UNCERTAIN','secondary_barrier':'UNKNOWN','evidence_complete':'INCOMPLETE','review_boundary':'ABSENT'}),
   ('REVIEW',{'current_relation':'SAME_FUNCTION','secondary_barrier':'UNKNOWN','evidence_complete':'COMPLETE','review_boundary':'PRESENT'})]
  for tr,z0 in states:
   z={'verification':ver,'successor_state':successor,**z0};rule,reaction=oracle(z);ctx=f'CTX-{ctxn:06d}';ctxn+=1;ct=ft+timedelta(days=65)
   if tr=='BASE': texts=['The support difficulty described in the earlier formation events is reported again.','The present record concerns the same support activity and time horizon as the earlier episode.']
   elif tr=='SECONDARY': texts=[f'The earlier support difficulty is reported again, and a separate observation is consistent with {alt.lower()}.','Both observations concern the same current support activity.']
   elif tr=='DIFFERENT': texts=[f'The earlier episode concerned {ac.lower()}.',f'The current observations concern {alt.lower()}, with no current observation about {ac.lower()}.']
   elif tr=='MISSING': texts=['The current record contains supply and support-action information.','The latest account of how the plan is being managed predates the current support period.']
   else: texts=['A new experience is reported during the current support period.','No authorised review record is present, and professional assessment is requested before proceeding.']
   ce=[]
   for i,t in enumerate(texts):ce.append({'context_id':ctx,'event_id':eid(),'patient_id':pat,'event_time':(ct+timedelta(days=i)).isoformat(),'source':'patient_report' if i==0 else 'support_record','role':'current_observation','content':t})
   cur_events+=ce;contexts.append({'context_id':ctx,'episode_id':ep,'transform':tr,'current_event_ids':'|'.join(x['event_id'] for x in ce)})
   # Evidence groups: historical required for base/secondary; current always required.
   current_groups=[[x['event_id'] for x in ce]]
   historical_groups=[[rr[0]['event_id'],rr[1]['event_id']]] if tr in ('BASE','SECONDARY') else []
   cond_evidence={c:{'historical_groups':historical_groups,'current_groups':current_groups} for c in CONDS}
   ref={'context_id':ctx,'episode_id':ep,'oracle_state':z,'oracle_decision':{'reaction':reaction,'rule_id':rule},'acceptable_evidence':cond_evidence};ref['reference_hash']=H(ref);refs.append(ref)
   challenge={'context_id':ctx,'primary_candidate':tr in ('BASE','SECONDARY'),'current_only_deterministic':tr not in ('BASE','SECONDARY'),'historical_resolution_required':tr in ('BASE','SECONDARY'),'verified_memory_decision_relevant':tr in ('BASE','SECONDARY'),'explicit_policy_phrase_present':False,'oracle_variable_named_directly':False,'at_least_two_open_loop_interpretations':tr in ('BASE','SECONDARY')};flags.append(challenge)
   common={'world_specification_id':'MSW-0.4.2','shared_world_rules':shared,'task':'Recover the oracle-defined reaction. Return one JSON object only.','reaction_vocabulary':RX,'rule_vocabulary':rule_vocab,'response_schema':response_schema,'current_records':ce}
   b0={**common,'condition':'B0_LLM_ALONE','longitudinal_records':fe+rr}
   m0={**common,'condition':'M0_OPEN_LOOP_MEMORY','longitudinal_records':fe+rr,'open_loop_memory':prospective}
   b1={**common,'condition':'B1_VERIFIED_MEMORY','longitudinal_records':fe+rr,'verified_cognitive_memory':memory}
   for cond,p in zip(CONDS,[b0,m0,b1]):
    call=f'CALL-{calln:07d}';calln+=1;calls.append({'call_id':call,'context_id':ctx,'episode_id':ep,'condition':cond,'payload':p});manifest.append({'call_id':call,'context_id':ctx,'episode_id':ep,'condition':cond})
# write files
write(R/'data/episodes.csv',episodes);write(R/'data/historical_events.csv',hist_events);write(R/'data/cognitive_memories.csv',memories);write(R/'data/current_contexts.csv',contexts);write(R/'data/current_events.csv',cur_events);write(R/'hidden/latent_episode_states.csv',latent);write(R/'data/challenge_flags.csv',flags);write(R/'prompts/model_call_manifest.csv',manifest)
with (R/'hidden/oracle_references.jsonl').open('w') as f:
 for x in refs:f.write(json.dumps(x,separators=(',',':'))+'\n')
with (R/'prompts/model_calls.jsonl').open('w') as f:
 for x in calls:f.write(json.dumps(x,separators=(',',':'))+'\n')
# one development episode per assumption, rotating verification; 21 reserved
byass={a:[x for x in episodes if x['assumption']==a] for a in ASS};dev=set(byass[a][i%4]['episode_id'] for i,a in enumerate(ASS));write(R/'data/split_manifest.csv',[{'episode_id':x['episode_id'],'split':'DEVELOPMENT' if x['episode_id'] in dev else 'RESERVED'} for x in episodes])
(R/'config/generation_schema.json').write_text(json.dumps({'version':'0.4.2','seed':SEED,'episodes':28,'contexts':140,'calls':420,'conditions':CONDS,'primary_transforms':['BASE','SECONDARY'],'primary_contrast':'B1-B0','mechanism_contrast':'B1-M0'},indent=2))
print(json.dumps({'episodes':len(episodes),'contexts':len(contexts),'calls':len(calls),'reactions':dict(Counter(x['oracle_decision']['reaction'] for x in refs))},indent=2))
