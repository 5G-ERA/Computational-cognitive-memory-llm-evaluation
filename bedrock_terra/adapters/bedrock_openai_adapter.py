"""Bedrock adapter for the OpenAI-compatible Chat Completions endpoint.

Drop-in replacement for OpenAICompatibleAdapterQA1: same constructor shape
(adapter = Cls(cfg)) and the same invoke(call) return contract, so
scripts/api_runner_qa1.py can use it without modification.

Four differences from the qa1 adapter, each forced by Bedrock:

1. Output ceiling field name is configurable ("max_tokens_field"). The GPT-5.x
   family uses "max_completion_tokens"; sending "max_tokens" risks the ceiling
   being silently ignored rather than rejected. Probe P4 decides the value.

2. Sampling parameters are opt-in ("send_sampling_params"). Current reasoning
   models reject non-default temperature/top_p with HTTP 400. The qa1 adapter
   sent them unconditionally, which would fail on call #1.

3. Reasoning text returned in a SEPARATE field (reasoning_content /
   reasoning) is NOT concatenated into assistant_text. Merging it would feed
   reasoning into the frozen extraction path and change what
   parse_final_answer sees. It is recorded in provider_metadata as evidence
   only. assistant_text stays exactly the final message content.

4. provider_metadata records the served model id, so the run manifest carries
   the version actually invoked rather than the alias requested.
"""
from __future__ import annotations
import json, os, time, urllib.request, urllib.error

SYSTEM_MESSAGE = ('Apply the disclosed synthetic-world rules. '
                  'Return exactly one JSON object matching response_schema.')

_REASONING_FIELDS = ('reasoning_content', 'reasoning', 'thinking')


class TransportHTTPError(Exception):
    """HTTP failure carrying the status code AND the provider's response body."""
    def __init__(self, code, body):
        self.code = code
        self.body = body
        super().__init__('HTTP {0}: {1}'.format(code, str(body)[:500]))


class BudgetExceeded(BaseException):
    """Client-side hard stop. Raised BEFORE issuing a call that would breach the cap.

    Deliberately derives from BaseException, NOT Exception.

    qa_runner.run_calls wraps adapter.invoke in a bare `except Exception`. An
    Exception subclass here would be swallowed by that handler, fail
    classify_terminal (no HTTP code, no context-length pattern), fall through to
    the retry path, burn all 3 attempts with backoff, and finally be recorded as
    TRANSPORT_SERVER_ERROR_EXHAUSTED + restartable -- for every remaining call in
    the split. A budget stop would masquerade as a mass transport failure and
    spin for hours.

    Giving it .code = 400 instead would make classify_terminal return
    CLIENT_CONFIGURATION_ERROR, which is in TERMINAL_EXACT: the untouched calls
    would be written to the registry as terminal and then SKIPPED on restart,
    permanently. That is worse.

    As a BaseException it escapes the handler, the process aborts, and because
    nothing is written to call_registry.jsonl for calls never attempted, a
    restart resumes exactly where it stopped. Hitting the cap is therefore safe
    and fully recoverable, which is what makes a tight cap the right choice.
    """


class CostGuard:
    """Deterministic client-side spend cap.

    AWS has no native hard spend cap for Bedrock. AWS Budgets alerts on billing
    data that lags hours behind, which is useless against a retry loop. This
    workload is bounded and countable (1800 calls, known token distribution), so
    the cap belongs in the client where it is instant and exact.

    Priced from the per-1M rates recorded in the model config, so the number the
    guard enforces is the same number the freeze record reports.
    """
    def __init__(self, cap_usd, price_in, price_out):
        self.cap = cap_usd
        self.pi = price_in or 0.0
        self.po = price_out or 0.0
        self.in_tokens = 0
        self.out_tokens = 0
        self.calls = 0

    @property
    def spent(self):
        return self.in_tokens / 1e6 * self.pi + self.out_tokens / 1e6 * self.po

    def check(self):
        if self.cap is not None and self.spent >= self.cap:
            raise BudgetExceeded(
                'BUDGET_EXCEEDED: %.4f USD spent of %.2f cap after %d calls '
                '(in=%d out=%d). Nothing further was sent.'
                % (self.spent, self.cap, self.calls, self.in_tokens, self.out_tokens))

    def add(self, in_tokens, out_tokens):
        self.in_tokens += in_tokens or 0
        self.out_tokens += out_tokens or 0
        self.calls += 1

    def summary(self):
        return {'calls': self.calls, 'input_tokens': self.in_tokens,
                'output_tokens': self.out_tokens, 'spent_usd': round(self.spent, 4),
                'cap_usd': self.cap}


class BedrockOpenAIAdapter:
    def __init__(self, config):
        self.cfg = config
        self.url = config['api_url']
        self.requires_key = config.get('requires_api_key', True)
        env = config.get('api_key_env', 'AWS_BEARER_TOKEN_BEDROCK')
        self.key = os.environ.get(env) if self.requires_key else None
        if not self.url:
            raise RuntimeError('CLIENT_CONFIGURATION_ERROR: missing api_url')
        if self.requires_key and not self.key:
            raise RuntimeError(
                'CLIENT_CONFIGURATION_ERROR: %s is not set in the environment' % env)
        if str(config.get('model', '')).startswith('PENDING'):
            raise RuntimeError(
                'CLIENT_CONFIGURATION_ERROR: model id is still PENDING_PROBE. '
                'Run probe_bedrock.py P0 and record the resolved id first.')

        # Interlock: an unbounded output ceiling is the single largest bill risk
        # here. If P4 has not established which field actually bites, refuse.
        field = config.get('max_tokens_field')
        if config.get('enforce_output_ceiling', True) and (
                not field or str(field).startswith('PENDING')):
            raise RuntimeError(
                'CLIENT_CONFIGURATION_ERROR: max_tokens_field is unresolved, so no '
                'output ceiling would be sent. Run probe P4 first, or set '
                '"enforce_output_ceiling": false to override deliberately.')

        self.guard = CostGuard(config.get('max_run_cost_usd'),
                               config.get('price_per_1m_input_usd'),
                               config.get('price_per_1m_output_usd'))

    def build_body(self, call, overrides=None):
        """Request body. Separated from invoke() so probes reuse the exact shape."""
        cfg = self.cfg
        body = {
            'model': cfg['model'],
            'messages': [
                {'role': 'system', 'content': cfg.get('system_message', SYSTEM_MESSAGE)},
                {'role': 'user', 'content': json.dumps(call['payload'])},
            ],
        }
        field = cfg.get('max_tokens_field', 'max_completion_tokens')
        if not str(field).startswith('PENDING'):
            body[field] = cfg.get('max_output_tokens', 4096)
        if cfg.get('send_sampling_params'):
            for k in ('temperature', 'top_p', 'seed'):
                if cfg.get(k) is not None:
                    body[k] = cfg[k]
        if cfg.get('reasoning_effort'):
            body['reasoning_effort'] = cfg['reasoning_effort']
        if cfg.get('service_tier'):
            body['service_tier'] = cfg['service_tier']
        if overrides:
            for k, v in overrides.items():
                if v is None:
                    body.pop(k, None)
                else:
                    body[k] = v
        return body

    def post(self, body):
        """Raw POST. Returns (parsed_json, latency_ms). Raises TransportHTTPError."""
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(), headers=headers)
        t = time.time()
        try:
            with urllib.request.urlopen(
                    req, timeout=self.cfg.get('timeout_seconds', 900)) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                payload = e.read().decode('utf-8', 'replace')
            except Exception:
                payload = e.reason or ''
            raise TransportHTTPError(e.code, payload)
        return data, round((time.time() - t) * 1000)

    def invoke(self, call):
        self.guard.check()
        data, latency = self.post(self.build_body(call))
        ch = (data.get('choices') or [{}])[0]
        msg = ch.get('message') or {}
        u = data.get('usage') or {}
        reasoning = next(
            (msg[f] for f in _REASONING_FIELDS if msg.get(f)), None)
        details = u.get('completion_tokens_details') or {}
        self.guard.add(u.get('prompt_tokens'), u.get('completion_tokens'))
        return {
            'http_status': 200,
            'provider_request_id': data.get('id', ''),
            'assistant_text': msg.get('content') or '',
            'structured_object': None,
            'finish_reason': ch.get('finish_reason'),
            'input_tokens': u.get('prompt_tokens'),
            'output_tokens': u.get('completion_tokens'),
            'latency_ms': latency,
            'provider_metadata': {
                'served_model': data.get('model'),
                'system_fingerprint': data.get('system_fingerprint'),
                'service_tier': data.get('service_tier'),
                'reasoning_returned_separately': reasoning is not None,
                'reasoning_chars': len(reasoning) if reasoning else 0,
                'reasoning_tokens': details.get('reasoning_tokens'),
                'cached_input_tokens': (u.get('prompt_tokens_details') or {}).get('cached_tokens'),
                'budget': self.guard.summary(),
            },
        }
