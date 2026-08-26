class MockAdapter:
 def __init__(self,refs):self.refs=refs
 def invoke(self,call,config):
  r=self.refs[call['context_id']];ev=r['acceptable_evidence'][call['condition']];ids=[]
  if ev['historical_groups']:ids+=ev['historical_groups'][0]
  if ev['current_groups']:ids+=ev['current_groups'][0]
  o={**r['oracle_decision'],'decisive_event_ids':list(dict.fromkeys(ids)),'reason':'Applied the first matching disclosed world rule to the supplied historical and current evidence.'}
  return {'http_status':200,'provider_request_id':'mock-'+call['call_id'],'assistant_text':__import__('json').dumps(o),'structured_object':o,'finish_reason':'stop','input_tokens':0,'output_tokens':0,'latency_ms':1,'provider_metadata':{'mock':True}}
