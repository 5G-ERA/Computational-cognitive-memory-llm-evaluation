from __future__ import annotations
import json,os,time,urllib.request,urllib.error

class TransportHTTPError(Exception):
    """HTTP failure carrying the status code AND the provider's response body.

    urllib.error.HTTPError stringifies to 'HTTP Error 400: Bad Request' and drops the
    body, so a context-length message from the server is invisible to the runner's
    terminal-status classifier. Reading the body here keeps that classification possible.
    """
    def __init__(self,code,body):
        self.code=code;self.body=body
        super().__init__('HTTP {0}: {1}'.format(code,body[:500]))

SYSTEM_MESSAGE='Apply the disclosed synthetic-world rules. Return exactly one JSON object matching response_schema.'

class OpenAICompatibleAdapterQA1:
    """OpenAI-compatible adapter with keyless support and finish_reason propagation.

    Section 8 of the qa1 protocol permits keyless endpoints when the model configuration
    declares them explicitly ("requires_api_key": false). Each call is an independent
    conversation: conversation_id is never sent, so server-side history cannot leak
    between calls.
    """
    def __init__(self,config):
        self.cfg=config
        self.url=config['api_url']
        self.requires_key=config.get('requires_api_key',True)
        self.key=os.environ.get(config.get('api_key_env','LLM_API_KEY')) if self.requires_key else None
        if not self.url:raise RuntimeError('CLIENT_CONFIGURATION_ERROR: missing api_url')
        if self.requires_key and not self.key:raise RuntimeError('CLIENT_CONFIGURATION_ERROR: missing API key')

    def invoke(self,call):
        cfg=self.cfg
        body={'model':cfg['model'],
              'messages':[{'role':'system','content':cfg.get('system_message',SYSTEM_MESSAGE)},
                          {'role':'user','content':json.dumps(call['payload'])}],
              'temperature':cfg.get('temperature',0),'top_p':cfg.get('top_p',1),
              'max_tokens':cfg.get('max_output_tokens',4096)}
        if cfg.get('seed') is not None:body['seed']=cfg['seed']
        headers={'Content-Type':'application/json'}
        if self.key:headers['Authorization']='Bearer '+self.key
        req=urllib.request.Request(self.url,data=json.dumps(body).encode(),headers=headers)
        t=time.time()
        try:
            with urllib.request.urlopen(req,timeout=cfg.get('timeout_seconds',900)) as resp:
                data=json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:body=e.read().decode('utf-8','replace')
            except Exception:body=e.reason or ''
            raise TransportHTTPError(e.code,body)
        ch=data['choices'][0];u=data.get('usage') or {}
        return {'http_status':200,'provider_request_id':data.get('id',''),
                'assistant_text':ch['message'].get('content') or '','structured_object':None,
                'finish_reason':ch.get('finish_reason'),
                'input_tokens':u.get('prompt_tokens'),'output_tokens':u.get('completion_tokens'),
                'latency_ms':round((time.time()-t)*1000),
                'provider_metadata':{'model':data.get('model'),'system_fingerprint':data.get('system_fingerprint')}}
