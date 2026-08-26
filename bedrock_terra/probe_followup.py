#!/usr/bin/env python3
"""Two items the first probe run left open.

P2b  response_format: the first run returned 403 with a Marketplace-permission
     body, i.e. a stale-authorisation artifact, NOT a statement about
     response_format. Re-run now that the permission has propagated.

P9   seed repeatability: P3 established that `seed` is ACCEPTED. Accepted is
     not honoured. The only test that matters for a frozen protocol is whether
     the same seed produces the same output, so send the same call three times
     and diff.
"""
import json, sys, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from adapters.bedrock_openai_adapter import BedrockOpenAIAdapter, TransportHTTPError

RELEASE = HERE.parent / 'release_qa1c' / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1c'
cfg = json.load(open(sys.argv[1]))
ad = BedrockOpenAIAdapter(dict(cfg, enforce_output_ceiling=False))

import csv, random
sp = {r['memory_id']: r['split'].lower()
      for r in csv.DictReader(open(RELEASE / 'data_v0_5_1/split_manifest.csv'))}
calls = [json.loads(x) for x in open(RELEASE / 'prompts/model_calls_v0_5_1.jsonl')]
calls = [c for c in calls if sp[c['memory_id']] == 'development']
random.Random(13082652).shuffle(calls)
call = calls[1]

out = {}

def post(ov):
    try:
        data, ms = ad.post(ad.build_body(call, ov))
        ch = data['choices'][0]
        return {'ok': True, 'content': ch['message'].get('content') or '',
                'finish': ch.get('finish_reason'),
                'out_tokens': data['usage']['completion_tokens']}
    except TransportHTTPError as e:
        return {'ok': False, 'http': e.code, 'body': str(e.body)[:300]}

print('P2b  response_format=json_object')
r = post({'response_format': {'type': 'json_object'}, 'max_completion_tokens': 256, 'max_tokens': None})
if not r['ok']:
    v = 'REJECTED_HTTP_%s' % r['http']
else:
    try:
        json.loads(r['content'].strip()); v = 'ACCEPTED_AND_JSON'
    except Exception:
        v = 'ACCEPTED_BUT_NOT_JSON'
out['P2b'] = {'verdict': v, 'call': r}
print('  verdict:', v)
if not r['ok']:
    print('  body:', r['body'][:200])

print('\nP9   seed repeatability (3 llamadas identicas, seed fijo)')
seen = []
for i in range(3):
    ov = {'seed': 13082642, 'top_p': 1, 'max_completion_tokens': 512, 'max_tokens': None}
    r = post(ov)
    if not r['ok']:
        print('  intento %d -> HTTP %s' % (i + 1, r['http'])); seen.append(None); continue
    h = hashlib.sha256(r['content'].encode()).hexdigest()[:12]
    seen.append(h)
    print('  intento %d -> sha=%s out=%s' % (i + 1, h, r['out_tokens']))
uniq = {h for h in seen if h}
out['P9'] = {'hashes': seen, 'distinct': len(uniq),
             'verdict': ('SEED_REPRODUCIBLE' if len(uniq) == 1 and None not in seen
                         else 'SEED_ACCEPTED_BUT_NOT_REPRODUCIBLE' if len(uniq) > 1
                         else 'INCONCLUSIVE')}
print('  verdict:', out['P9']['verdict'], '(%d salida(s) distinta(s))' % out['P9']['distinct'])

Path('out/followup_%s.json' % Path(sys.argv[1]).stem).write_text(json.dumps(out, indent=2))
