"""Production fault behaviour for the v0.5.1-qa1b runner.

Covers the section 6 release requirement: 'Verify retry, timeout, context limit, client
error, full outage, restart, and duplicate-terminal behaviour against the production
runner.' Every scenario drives the SHIPPED adapter (OpenAICompatibleAdapterQA1) and the
SHIPPED runner (qa_runner.run_calls) against a local fault-injection endpoint. No model
is contacted and no benchmark item is consumed.

    python tests/test_production_faults_qa1b.py
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))

from adapters.openai_compatible_adapter_qa1 import OpenAICompatibleAdapterQA1  # noqa: E402
from qa_runner import run_calls  # noqa: E402

KIMI_REPLY = ('◁think▷ Weighing the historical scope against the current marker. '
              '{"reaction":"DRAFT","note":"discarded draft"} On reflection that draft is wrong. '
              '◁/think▷\n{"reaction":"CONTINUE_SUPPORT","rule_id":"R10_CONFIRMED_CONTINUATION",'
              '"decisive_event_ids":["EVT-0000002"],"justification":"resolved"}')

PLAN = {}          # call_id -> list of scripted outcomes, consumed in order
SEEN = []          # every request the server received


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n) or b'{}')
        SEEN.append({'headers': dict(self.headers), 'body': body})
        # The adapter sends json.dumps(call['payload']), so the scripted key arrives encoded.
        raw = body['messages'][-1]['content']
        try:
            cid = json.loads(raw)
        except ValueError:
            cid = raw
        steps = PLAN.get(cid, ['ok'])
        step = steps.pop(0) if steps else 'ok'

        if step == 'slow':
            time.sleep(3)
            step = 'ok'
        if isinstance(step, int):
            self.send_error(step, 'injected {0}'.format(step))
            return
        if step == 'ctx500':
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': {'message':
                             'failed to decode: the request exceeds n_ctx'}}).encode())
            return
        if step == 'ctx':
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': {'message':
                             'the request exceeds the maximum context length (n_ctx)'}}).encode())
            return
        finish = 'length' if step == 'truncated' else 'stop'
        text = KIMI_REPLY[:120] if step == 'truncated' else KIMI_REPLY
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'id': 'resp-1', 'model': 'kimi-dev-72b',
            'choices': [{'message': {'role': 'assistant', 'content': text},
                         'finish_reason': finish}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50}}).encode())


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Endpoint:
    """Fault-injection endpoint that can be stopped and restarted on a stable port."""

    def __init__(self, port):
        self.port = port
        self.srv = None

    def start(self):
        self.srv = ThreadingHTTPServer(('127.0.0.1', self.port), Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        if self.srv:
            self.srv.shutdown()
            self.srv.server_close()
            self.srv = None


FAST_RETRY = {'max_attempts': 3, 'backoff_seconds': [0, 0, 0], 'jitter_seed': 13082653,
              'failed_retryable_calls_are_restartable': True}

RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond), detail))
    print('  {0} {1}{2}'.format('PASS' if cond else 'FAIL', name,
                                ' :: ' + detail if detail and not cond else ''))


def call(cid):
    return {'call_id': cid, 'payload': cid}


def read(out, name):
    p = Path(out) / name
    return [json.loads(x) for x in p.open()] if p.exists() else []


def scenario(tmp, port, name, plan, cids, timeout_seconds=30):
    PLAN.clear()
    PLAN.update(plan)
    cfg = {'model': 'kimi-dev-72b', 'api_url': 'http://127.0.0.1:{0}/v1/chat/completions'.format(port),
           'requires_api_key': False, 'temperature': 0, 'max_output_tokens': 4096,
           'timeout_seconds': timeout_seconds}
    out = Path(tmp) / name
    adapter = OpenAICompatibleAdapterQA1(cfg)
    report = run_calls([call(c) for c in cids], adapter, out, FAST_RETRY)
    return out, report


def main():
    tmp = tempfile.mkdtemp(prefix='qa1b_faults_')
    port = free_port()
    ep = Endpoint(port)
    ep.start()
    try:
        print('1. transient faults are retried and then succeed')
        out, rep = scenario(tmp, port, 's1', {'c1': [429, 'ok'], 'c2': [500, 503, 'ok']},
                            ['c1', 'c2'])
        att = read(out, 'attempts.jsonl')
        reg = read(out, 'call_registry.jsonl')
        check('429 then success is retried once',
              [a['attempt'] for a in att if a['call_id'] == 'c1'] == [1, 2])
        check('500 then 503 then success takes three attempts',
              [a['attempt'] for a in att if a['call_id'] == 'c2'] == [1, 2, 3])
        check('both calls reach a terminal record', len(reg) == 2)
        check('terminal status is COMPLETED_VALID',
              {r['terminal_status'] for r in reg} == {'COMPLETED_VALID'})

        print('2. real Kimi unicode markers are parsed, drafts discarded')
        parsed = read(out, 'responses_parsed.jsonl')
        obj = [p['parsed'] for p in parsed if p['status'] == 'COMPLETED_VALID'][0]
        check('final object taken from after the unicode end marker',
              obj['reaction'] == 'CONTINUE_SUPPORT', json.dumps(obj))
        check('draft object inside the reasoning block ignored', obj.get('note') is None)

        print('3. keyless and stateless transport')
        check('no Authorization header is sent',
              all('Authorization' not in s['headers'] for s in SEEN))
        check('conversation_id is never sent',
              all('conversation_id' not in s['body'] for s in SEEN))
        check('system message is present in every request',
              all(s['body']['messages'][0]['role'] == 'system' for s in SEEN))
        check('max_tokens ceiling is propagated',
              all(s['body'].get('max_tokens') == 4096 for s in SEEN))

        print('4. finish_reason=length is a truncation, not a parse failure')
        out, rep = scenario(tmp, port, 's4', {'c1': ['truncated']}, ['c1'])
        reg = read(out, 'call_registry.jsonl')
        check('truncated reply classified COMPLETED_OUTPUT_TRUNCATED',
              reg[0]['terminal_status'] == 'COMPLETED_OUTPUT_TRUNCATED', reg[0]['terminal_status'])
        check('truncation is terminal and not retried',
              len(read(out, 'attempts.jsonl')) == 1)

        print('5. client error is terminal and never retried')
        out, rep = scenario(tmp, port, 's5', {'c1': [401, 401, 401]}, ['c1'])
        att = read(out, 'attempts.jsonl')
        reg = read(out, 'call_registry.jsonl')
        check('401 stops after one attempt', len(att) == 1, json.dumps(att))
        check('401 classified CLIENT_CONFIGURATION_ERROR',
              reg and reg[0]['terminal_status'] == 'CLIENT_CONFIGURATION_ERROR',
              json.dumps(reg))

        print('6. context limit is terminal and never retried')
        out, rep = scenario(tmp, port, 's6', {'c1': ['ctx', 'ctx', 'ctx']}, ['c1'])
        att = read(out, 'attempts.jsonl')
        reg = read(out, 'call_registry.jsonl')
        check('context-limit error stops after one attempt', len(att) == 1, json.dumps(att))
        check('context-limit classified TRANSPORT_CONTEXT_LIMIT',
              reg and reg[0]['terminal_status'] == 'TRANSPORT_CONTEXT_LIMIT', json.dumps(reg))

        print('6b. a context limit reported as 500 is still terminal')
        out, rep = scenario(tmp, port, 's6b', {'c1': ['ctx500', 'ctx500', 'ctx500']}, ['c1'])
        att = read(out, 'attempts.jsonl')
        reg = read(out, 'call_registry.jsonl')
        check('500-carried context limit stops after one attempt', len(att) == 1,
              json.dumps(att))
        check('500-carried context limit classified TRANSPORT_CONTEXT_LIMIT',
              reg and reg[0]['terminal_status'] == 'TRANSPORT_CONTEXT_LIMIT', json.dumps(reg))
        check('500-carried context limit is not restartable',
              not any(a.get('restartable') for a in att))

        print('7. timeout is retried')
        out, rep = scenario(tmp, port, 's7', {'c1': ['slow', 'ok']}, ['c1'], timeout_seconds=1)
        att = read(out, 'attempts.jsonl')
        check('timeout produces a retryable attempt then a success',
              [a['outcome'] for a in att] == ['RETRYABLE_ERROR', 'COMPLETED_VALID'],
              json.dumps(att))

        print('8. exhausted retryable faults are restartable, not silently terminal')
        out, rep = scenario(tmp, port, 's8', {'c1': [429, 429, 429], 'c2': ['ok']}, ['c1', 'c2'])
        reg = read(out, 'call_registry.jsonl')
        att = read(out, 'attempts.jsonl')
        check('exhausted call is NOT written to the registry',
              [r['call_id'] for r in reg] == ['c2'], json.dumps(reg))
        check('exhausted call is marked restartable',
              any(a.get('restartable') and a['call_id'] == 'c1' for a in att))
        check('completion validator fails while a call is missing', rep['pass'] is False)
        check('completion validator names the shortfall',
              rep['expected'] == 2 and rep['terminal'] == 1, json.dumps(rep))

        print('9. restart after a full outage recovers exactly the missing calls')
        ep.stop()
        PLAN.clear()
        cfg = {'model': 'kimi-dev-72b',
               'api_url': 'http://127.0.0.1:{0}/v1/chat/completions'.format(port),
               'requires_api_key': False, 'timeout_seconds': 2}
        out9 = Path(tmp) / 's9'
        adapter = OpenAICompatibleAdapterQA1(cfg)
        rep = run_calls([call('c1'), call('c2')], adapter, out9, FAST_RETRY)
        check('total outage leaves the registry empty', read(out9, 'call_registry.jsonl') == [])
        check('total outage fails the completion validator', rep['pass'] is False)
        ep.start()
        PLAN.clear()
        rep2 = run_calls([call('c1'), call('c2')], adapter, out9, FAST_RETRY)
        reg = read(out9, 'call_registry.jsonl')
        check('restart recovers every call', rep2['pass'] is True, json.dumps(rep2))
        check('restart produces no duplicate terminal record',
              len(reg) == len({r['call_id'] for r in reg}) == 2, json.dumps(reg))

        print('10. re-running a complete run adds nothing')
        before = len(read(out9, 'call_registry.jsonl'))
        n_seen = len(SEEN)
        rep3 = run_calls([call('c1'), call('c2')], adapter, out9, FAST_RETRY)
        check('already-terminal calls are skipped', len(SEEN) == n_seen)
        check('registry is unchanged', len(read(out9, 'call_registry.jsonl')) == before)
        check('duplicate-terminal guard still passes', rep3['no_duplicate_terminal'] is True)

        print('11. the shipped retry policy matches the frozen specification')
        pol = json.loads((R / 'config/retry_policy.json').read_text())
        check('retryable statuses are 429 and 5xx only',
              sorted(pol['retry_http_status']) == [429, 500, 502, 503, 504])
        check('client errors listed as non-retryable',
              401 in pol['non_retryable_http_status'] and 400 in pol['non_retryable_http_status'])
        check('model output is never retried', pol['retry_model_output'] is False)
        check('max attempts is 3', pol['max_attempts'] == 3)
    finally:
        ep.stop()
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [n for n, ok, _ in RESULTS if not ok]
    print('\n{0}/{1} checks passed'.format(len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print('FAILED: ' + ', '.join(failed))
    json.dump({'suite': 'production_faults_qa1b',
               'checks': [{'name': n, 'pass': ok} for n, ok, _ in RESULTS],
               'passed': len(RESULTS) - len(failed), 'total': len(RESULTS),
               'status': 'PASS' if not failed else 'FAIL'},
              open(R / 'validation/production_fault_tests_qa1b.json', 'w'), indent=2)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
