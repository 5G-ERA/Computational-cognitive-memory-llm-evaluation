#!/usr/bin/env python3
"""Pre-flight probes for a Bedrock arm of the v0.5.1 benchmark.

Answers, by measurement, the questions that must be settled BEFORE any
protocol decision is taken to Renxi and before a single reserved call is spent:

  P0  which model ids this account actually serves
  P1  is the system message respected, or silently dropped   (gate A1)
  P2  is response_format accepted, ignored, or rejected       (gate A2)
  P3  are temperature / top_p / seed accepted                 (determinism)
  P4  which output-ceiling field actually bites
  P5  how reasoning comes back, vs the frozen marker list
  P6  statelessness across calls
  P7  is reasoning_effort accepted, and what does it cost
  P8  one real DEVELOPMENT call end-to-end through the frozen parser

Reads the frozen release read-only. Uses the DEVELOPMENT split only; asserts
this before issuing any call. Total cost is a few cents.

  export AWS_BEARER_TOKEN_BEDROCK=...
  python3 probe_bedrock.py --config config/model_terra_bedrock.json
  python3 probe_bedrock.py --config config/model_terra_bedrock.json --dry-run
"""
from __future__ import annotations
import argparse, csv, json, random, sys, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_RELEASE = (HERE.parent / 'release_qa1c'
                   / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1c')
FALLBACK_END = ("</think>", "<|end_of_thought|>", "<|end_of_think|>", "◁/think▷", "◁/think")
FALLBACK_START = ("<think>", "<|begin_of_thought|>", "◁think▷")
NONCE = 'ZQ7-ORANGE-4419'


def load_frozen(release: Path):
    """Import the frozen parser and marker list. Never writes to the release.

    sys.dont_write_bytecode is set before the import: without it CPython drops a
    __pycache__/ directory inside the frozen package, which is an unlisted file
    against the release manifest.
    """
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(release / 'scripts'))
    end, start, parse_final, schema_errors = FALLBACK_END, FALLBACK_START, None, None
    try:
        import qa_core
        end, start = qa_core.load_markers(release / 'config/extraction_policy.json')
        parse_final = qa_core.parse_final_answer
    except Exception as e:
        print('  ! qa_core unavailable (%s); falling back to literal markers' % e)
    try:
        from core import schema_errors as se
        schema_errors = se
    except Exception:
        pass
    return end, start, parse_final, schema_errors


def dev_calls(release: Path, n=2):
    sp = {r['memory_id']: r['split'].lower()
          for r in csv.DictReader(open(release / 'data_v0_5_1/split_manifest.csv'))}
    calls = [json.loads(x) for x in open(release / 'prompts/model_calls_v0_5_1.jsonl')]
    calls = [c for c in calls if sp[c['memory_id']] == 'development']
    assert calls, 'no development calls found'
    bad = [c for c in calls if sp[c['memory_id']] != 'development']
    assert not bad, 'RESERVED call leaked into the probe set'
    random.Random(13082652).shuffle(calls)
    return calls[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--release', default=str(DEFAULT_RELEASE))
    ap.add_argument('--out', default=str(HERE / 'out'))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    release = Path(a.release)
    cfg = json.load(open(a.config))
    end_markers, start_markers, parse_final, schema_errors = load_frozen(release)
    calls = dev_calls(release, 2)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(HERE))
    from adapters.bedrock_openai_adapter import BedrockOpenAIAdapter, TransportHTTPError

    R = {'config_file': a.config, 'model_requested': cfg.get('model'),
         'release': str(release), 'probes': {}}

    # Only INPUTS block a live run. model_snapshot / endpoint_verified are
    # OUTPUTS the probe itself resolves, so requiring them would be circular.
    # max_tokens_field is deliberately NOT here: probe P4 exists to discover it,
    # so requiring it up front would be circular. The adapter's interlock still
    # protects the real run, which is where an absent ceiling costs money.
    INPUT_FIELDS = ('model', 'api_url')
    pending = sorted(k for k, v in cfg.items()
                     if k in INPUT_FIELDS and str(v).startswith('PENDING'))
    pending_out = sorted(k for k, v in cfg.items()
                         if k not in INPUT_FIELDS and str(v).startswith('PENDING'))

    if a.dry_run:
        cfg = dict(cfg, requires_api_key=False, enforce_output_ceiling=False)
        if str(cfg['model']).startswith('PENDING'):
            cfg['model'] = 'DRYRUN_PLACEHOLDER'
        ad = BedrockOpenAIAdapter(cfg)
        body = ad.build_body(calls[0])
        shown = dict(body, messages='<%d messages, %d chars of payload>' % (
            len(body['messages']), len(body['messages'][-1]['content'])))
        print(json.dumps(shown, indent=2))
        if pending:
            print('\n[dry-run] BLOCKING - inputs the probe cannot guess: %s' % ', '.join(pending))
        if pending_out:
            print('[dry-run] to be filled BY the probe (fine to leave): %s' % ', '.join(pending_out))
        if not any(k in body for k in ('max_tokens', 'max_completion_tokens')):
            print('[dry-run] WARNING: no output-ceiling field in the body. '
                  'Running like this means NO cap on output tokens.')
        print('\n[dry-run] no calls issued. Shape above is what P1-P8 would send.')
        return 0

    if pending:
        print('REFUSING TO RUN: unresolved config fields: %s' % ', '.join(pending))
        print('Resolve them from a previous probe (P0 for model ids, P4 for the '
              'ceiling field) before issuing live calls.')
        return 3
    try:
        # Probes set an explicit small ceiling on every call via overrides, and P4
        # is what establishes which field bites. Disable the interlock for the
        # probe run only; the config on disk keeps enforce_output_ceiling true.
        # 900s suits a production run; for a probe it means one hung call stalls
        # the whole sequence. Cap it.
        ad = BedrockOpenAIAdapter(dict(cfg, enforce_output_ceiling=False,
                                       timeout_seconds=min(cfg.get('timeout_seconds', 900), 180)))
    except RuntimeError as e:
        print('%s' % e)
        return 3

    CEIL = {'field': None}          # resolved by P4, applied to every later call

    def attempt(label, call, overrides=None):
        """One call. Never raises: every outcome is data.

        Injects a default output ceiling when the caller did not set one. A probe
        call with no ceiling is unbounded: it runs until the request timeout and
        bills an arbitrarily large completion. This is what hung the first Qwen3
        run for 15 minutes on a single call.
        """
        overrides = dict(overrides or {})
        if not any(k in overrides for k in ('max_tokens', 'max_completion_tokens')):
            overrides[CEIL['field'] or 'max_completion_tokens'] = cfg.get('max_output_tokens', 4096)
        body = ad.build_body(call, overrides)
        try:
            data, ms = ad.post(body)
            ch = (data.get('choices') or [{}])[0]
            msg = ch.get('message') or {}
            u = data.get('usage') or {}
            rec = {'ok': True, 'http': 200, 'latency_ms': ms,
                   'served_model': data.get('model'),
                   'finish_reason': ch.get('finish_reason'),
                   'prompt_tokens': u.get('prompt_tokens'),
                   'completion_tokens': u.get('completion_tokens'),
                   'reasoning_tokens': (u.get('completion_tokens_details') or {}).get('reasoning_tokens'),
                   'content': msg.get('content') or '',
                   'reasoning_field': next((f for f in ('reasoning_content', 'reasoning', 'thinking')
                                            if msg.get(f)), None)}
        except TransportHTTPError as e:
            rec = {'ok': False, 'http': e.code, 'body': str(e.body)[:600]}
        except Exception as e:
            rec = {'ok': False, 'http': None, 'body': '%s: %s' % (type(e).__name__, e)}
        print('  %-34s -> %s' % (label, 'HTTP %s' % rec['http'] if not rec['ok'] else
                                 'ok (in=%s out=%s fr=%s)' % (rec['prompt_tokens'],
                                                              rec['completion_tokens'],
                                                              rec['finish_reason'])))
        return rec

    # ---- P0: what does this account actually serve -------------------------
    print('\nP0  model listing')
    models_url = cfg['api_url'].rsplit('/chat/completions', 1)[0] + '/models'
    try:
        req = urllib.request.Request(
            models_url, headers={'Authorization': 'Bearer ' + (ad.key or '')})
        with urllib.request.urlopen(req, timeout=60) as r:
            ids = sorted(m.get('id', '') for m in (json.loads(r.read()).get('data') or []))
        R['probes']['P0'] = {'url': models_url, 'count': len(ids), 'ids': ids,
                             'terra': [i for i in ids if 'terra' in i.lower()],
                             'qwen': [i for i in ids if 'qwen' in i.lower()],
                             'requested_present': cfg.get('model') in ids}
        print('  %d ids; requested id present: %s'
              % (len(ids), R['probes']['P0']['requested_present']))
    except Exception as e:
        R['probes']['P0'] = {'error': '%s: %s' % (type(e).__name__, e), 'url': models_url}
        print('  ! %s' % e)

    # ---- P4: which ceiling field bites ------------------------------------
    print('\nP4  output ceiling field')
    ceil = {}
    for field in ('max_completion_tokens', 'max_tokens'):
        ov = {'max_completion_tokens': None, 'max_tokens': None, field: 16}
        r = attempt(field + '=16', calls[0], ov)
        ceil[field] = {'accepted': bool(r.get('ok')), 'http': r.get('http'),
                       'finish_reason': r.get('finish_reason'),
                       'completion_tokens': r.get('completion_tokens'),
                       'body': r.get('body')}
    def bites(d):
        return d['accepted'] and (d['finish_reason'] == 'length'
                                  or (d['completion_tokens'] or 999) <= 32)
    effective = [f for f, d in ceil.items() if bites(d)]
    R['probes']['P4'] = {'per_field': ceil, 'effective_fields': effective,
                         'recommended': (effective[0] if effective else 'UNRESOLVED')}
    print('  effective: %s' % (effective or 'none - ceiling may be IGNORED'))

    CEIL['field'] = (R['probes']['P4']['recommended']
                     if R['probes']['P4']['recommended'] != 'UNRESOLVED' else None)
    print('  campo de techo para el resto de probes: %s'
          % (CEIL['field'] or 'max_completion_tokens (por defecto)'))

    # ---- P1: system message respected (gate A1) ---------------------------
    print('\nP1  system message respected')
    pad = ' The following clause is padding to make the system block long enough that its presence must move the prompt token count.' * 12
    with_sys = attempt('with long system block', calls[0],
                       {'messages': [
                           {'role': 'system', 'content': 'Return one JSON object.' + pad},
                           {'role': 'user', 'content': json.dumps(calls[0]['payload'])}],
                        'max_completion_tokens': 16, 'max_tokens': None})
    no_sys = attempt('user only', calls[0],
                     {'messages': [{'role': 'user', 'content': json.dumps(calls[0]['payload'])}],
                      'max_completion_tokens': 16, 'max_tokens': None})
    verdict = 'INCONCLUSIVE'
    if with_sys.get('ok') and no_sys.get('ok'):
        pt1, pt0 = with_sys['prompt_tokens'], no_sys['prompt_tokens']
        if pt1 is None or pt0 is None:
            verdict = 'INCONCLUSIVE_NO_USAGE'
        elif pt1 == pt0:
            verdict = 'FAIL_SYSTEM_SILENTLY_DROPPED'
        else:
            verdict = 'PASS_SYSTEM_RESPECTED'
    R['probes']['P1'] = {'verdict': verdict, 'with_system': with_sys, 'without_system': no_sys}
    print('  verdict: %s' % verdict)

    # ---- P2: response_format (gate A2) ------------------------------------
    print('\nP2  response_format')
    rf = attempt('response_format=json_object', calls[0],
                 {'response_format': {'type': 'json_object'},
                  'max_completion_tokens': 256, 'max_tokens': None})
    if not rf.get('ok'):
        v2 = 'REJECTED_HTTP_%s' % rf['http']
    else:
        try:
            json.loads((rf.get('content') or '').strip()); v2 = 'ACCEPTED_AND_JSON'
        except Exception:
            v2 = 'ACCEPTED_BUT_NOT_JSON_probably_ignored'
    R['probes']['P2'] = {'verdict': v2, 'call': rf}
    print('  verdict: %s' % v2)

    # ---- P3: determinism parameters ---------------------------------------
    print('\nP3  determinism parameters')
    det = {}
    for name, ov in (('temperature=0', {'temperature': 0}),
                     ('top_p=1', {'top_p': 1}),
                     ('seed=13082642', {'seed': 13082642}),
                     ('all three', {'temperature': 0, 'top_p': 1, 'seed': 13082642})):
        ov = dict(ov, max_completion_tokens=16, max_tokens=None)
        r = attempt(name, calls[0], ov)
        det[name] = {'accepted': bool(r.get('ok')), 'http': r.get('http'),
                     'body': r.get('body')}
    accepted = [k for k, v in det.items() if v['accepted'] and k != 'all three']
    R['probes']['P3'] = {
        'per_param': det,
        'note': ('ACCEPTED is not HONOURED. This probe only establishes that the API does '
                 'not reject the parameters. Run probe_followup.py P9 to test whether the '
                 'same seed actually reproduces the same output.'),
        'verdict': ('DETERMINISM_PARAMS_ACCEPTED_pending_P9' if det.get('all three', {}).get('accepted')
                    else ('DETERMINISM_UNAVAILABLE_amendment_required'
                          if any(v.get('http') == 400 for v in det.values())
                          else 'INCONCLUSIVE_NON_400_FAILURE')),
        'accepted_params': accepted}
    print('  verdict: %s' % R['probes']['P3']['verdict'])

    # ---- P5 / P8: real dev call, markers, frozen parser --------------------
    print('\nP5/P8  real DEVELOPMENT call through the frozen parser')
    real = attempt('full dev call', calls[1], None)
    p5 = {'call': {k: v for k, v in real.items() if k != 'content'}}
    if real.get('ok'):
        txt = real.get('content') or ''
        p5['content_chars'] = len(txt)
        p5['content_head'] = txt[:400]
        p5['frozen_end_markers_found'] = [m for m in end_markers if m in txt]
        p5['frozen_start_markers_found'] = [m for m in start_markers if m in txt]
        p5['reasoning_in_separate_field'] = real.get('reasoning_field')
        p5['unlisted_marker_candidates'] = [
            m for m in ('<reasoning>', '</reasoning>', '<analysis>', '</analysis>',
                        '<|channel|>', '<|message|>', '<|start|>', '<|end|>')
            if m in txt]
        if not p5['frozen_end_markers_found'] and not p5['frozen_start_markers_found']:
            p5['marker_verdict'] = ('NO_MARKERS_IN_CONTENT_frozen_policy_parses_whole_message'
                                    if real.get('finish_reason') == 'stop'
                                    else 'NO_MARKERS_but_finish_reason_%s' % real.get('finish_reason'))
        elif p5['frozen_end_markers_found']:
            p5['marker_verdict'] = 'FROZEN_END_MARKER_PRESENT'
        else:
            p5['marker_verdict'] = 'START_WITHOUT_END_would_score_TRUNCATED'
        if parse_final:
            try:
                pr = parse_final(txt, None, real.get('finish_reason'),
                                 True, end_markers, start_markers)
                p5['frozen_parser_status'] = pr.status
                p5['frozen_parser_errors'] = pr.errors
                if pr.obj is not None and schema_errors:
                    p5['schema_errors'] = schema_errors(pr.obj)
            except Exception as e:
                p5['frozen_parser_status'] = 'PARSER_RAISED: %s' % e
    R['probes']['P5_P8'] = p5
    print('  markers: %s | parser: %s' % (p5.get('marker_verdict'),
                                          p5.get('frozen_parser_status')))

    # ---- P6: statelessness -------------------------------------------------
    print('\nP6  statelessness')
    a1 = attempt('turn 1 (plant nonce)', calls[0],
                 {'messages': [{'role': 'user',
                                'content': 'Remember this token and reply only OK: ' + NONCE}],
                  'max_completion_tokens': 32, 'max_tokens': None})
    a2 = attempt('turn 2 (ask for nonce)', calls[0],
                 {'messages': [{'role': 'user',
                                'content': 'What token did I just ask you to remember? '
                                           'If you were not told one, reply NONE.'}],
                  'max_completion_tokens': 32, 'max_tokens': None})
    if not (a1.get('ok') and a2.get('ok')):
        v6 = 'INCONCLUSIVE_CALLS_FAILED'   # never infer statelessness from failed calls
    elif NONCE in (a2.get('content') or ''):
        v6 = 'FAIL_STATE_LEAKED'
    else:
        v6 = 'PASS_STATELESS'
    R['probes']['P6'] = {'verdict': v6, 'turn2_content': (a2.get('content') or '')[:200]}
    print('  verdict: %s' % R['probes']['P6']['verdict'])

    # ---- P7: reasoning_effort ---------------------------------------------
    print('\nP7  reasoning_effort')
    eff = {}
    for lvl in ('low', 'medium', 'high'):
        r = attempt('reasoning_effort=%s' % lvl, calls[1],
                    {'reasoning_effort': lvl, 'max_completion_tokens': 2048, 'max_tokens': None})
        eff[lvl] = {'accepted': bool(r.get('ok')), 'http': r.get('http'),
                    'completion_tokens': r.get('completion_tokens'),
                    'reasoning_tokens': r.get('reasoning_tokens'),
                    'finish_reason': r.get('finish_reason'), 'body': r.get('body')}
    R['probes']['P7'] = {'per_level': eff,
                         'supported': [k for k, v in eff.items() if v['accepted']]}
    print('  supported: %s' % (R['probes']['P7']['supported'] or 'none'))

    # ---- report ------------------------------------------------------------
    stem = Path(a.config).stem
    (out / ('probe_%s.json' % stem)).write_text(json.dumps(R, indent=2, ensure_ascii=False))

    rows = [
        ('P0  model id served', str(R['probes'].get('P0', {}).get('requested_present'))),
        ('P1  system respected (A1)', R['probes'].get('P1', {}).get('verdict', '-')),
        ('P2  response_format (A2)', R['probes'].get('P2', {}).get('verdict', '-')),
        ('P3  determinism', R['probes'].get('P3', {}).get('verdict', '-')),
        ('P3  params accepted', ', '.join(R['probes'].get('P3', {}).get('accepted_params', [])) or 'none'),
        ('P4  effective ceiling field', R['probes'].get('P4', {}).get('recommended', '-')),
        ('P5  reasoning markers', R['probes'].get('P5_P8', {}).get('marker_verdict', '-')),
        ('P6  statelessness', R['probes'].get('P6', {}).get('verdict', '-')),
        ('P7  reasoning_effort', ', '.join(R['probes'].get('P7', {}).get('supported', [])) or 'none'),
        ('P8  frozen parser status', R['probes'].get('P5_P8', {}).get('frozen_parser_status', '-')),
    ]
    md = ['# Bedrock pre-flight probes — %s' % cfg.get('model'),
          '', 'Release probed read-only: `%s`' % release.name,
          '', '| Probe | Result |', '|---|---|']
    md += ['| %s | %s |' % r for r in rows]
    (out / ('probe_%s.md' % stem)).write_text('\n'.join(md) + '\n')

    print('\n' + '\n'.join('  %-30s %s' % r for r in rows))
    print('\nwrote %s' % (out / ('probe_%s.json' % stem)))
    print('wrote %s' % (out / ('probe_%s.md' % stem)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
