import json,os,urllib.request,time
class OpenAICompatibleAdapter:
 def invoke(self,call,config):
  key=os.environ.get(config.get('api_key_env','LLM_API_KEY'));url=config['api_url']
  if not key or not url:raise RuntimeError('Missing API key or api_url')
  body={'model':config['model'],'messages':[{'role':'system','content':'Apply the disclosed synthetic-world rules. Return exactly one JSON object matching response_schema.'},{'role':'user','content':json.dumps(call['payload'])}],'temperature':config.get('temperature',0),'top_p':config.get('top_p',1),'max_tokens':config.get('max_output_tokens',300)}
  req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key});t=time.time()
  with urllib.request.urlopen(req,timeout=config.get('timeout_seconds',120)) as resp:data=json.loads(resp.read())
  msg=data['choices'][0]['message']['content'];u=data.get('usage',{})
  return {'http_status':200,'provider_request_id':data.get('id',''),'assistant_text':msg,'structured_object':None,'finish_reason':data['choices'][0].get('finish_reason'),'input_tokens':u.get('prompt_tokens'),'output_tokens':u.get('completion_tokens'),'latency_ms':round((time.time()-t)*1000),'provider_metadata':{}}
