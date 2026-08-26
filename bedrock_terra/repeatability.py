#!/usr/bin/env python3
"""Run-to-run generation variability on one DEVELOPMENT memory.

Why this exists. With a non-deterministic arm a single execution stops being
"the result" and becomes one sample from a distribution of executions. The
clustered bootstrap over memories covers sampling variability across memories;
it does not tell you how far the point estimate would move if you re-ran the
whole thing. This measures exactly that, cheaply, on data that is already
unsealed.

Method. Take one development memory (45 calls), execute it N times through the
FROZEN parser and the FROZEN scorer, and compare runs at three levels:

  bytes     - is the returned text character-identical?
  decision  - same (reaction, rule_id, decisive_event_ids)?
  scored    - same reaction_correct / rule_correct?

Only the third level matters for the paper: two different sentences that score
identically do not move any endpoint. Reporting all three separates "the model
phrases things differently" from "the model decides differently".

  python3 repeatability.py --config config/model_terra_bedrock.json --runs 2
"""
from __future__ import annotations
import argparse, csv, hashlib, json, random, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_RELEASE = (HERE.parent / 'release_qa1c'
                   / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1c')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--release', default=str(DEFAULT_RELEASE))
    ap.add_argument('--runs', type=int, default=2)
    ap.add_argument('--memory', help='memory_id; default = first DEVELOPMENT memory by id')
    ap.add_argument('--out', default=str(HERE / 'out'))
    a = ap.parse_args()

    release = Path(a.release)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(release / 'scripts'))
    sys.path.insert(0, str(HERE))
    from qa_core import parse_final_answer, load_markers
    from core import schema_errors, interpret
    from adapters.bedrock_openai_adapter import (BedrockOpenAIAdapter, BudgetExceeded,
                                                 TransportHTTPError)

    end_m, start_m = load_markers(release / 'config/extraction_policy.json')
    sp = {r['memory_id']: r['split'].lower()
          for r in csv.DictReader(open(release / 'data_v0_5_1/split_manifest.csv'))}
    dev = sorted(m for m, s in sp.items() if s == 'development')
    mem = a.memory or dev[0]
    assert sp.get(mem) == 'development', \
        'REFUSING: %s is not in the DEVELOPMENT split (split=%s)' % (mem, sp.get(mem))

    calls = [json.loads(x) for x in open(release / 'prompts/model_calls_v0_5_1.jsonl')]
    calls = [c for c in calls if c['memory_id'] == mem]
    assert calls, 'no calls for %s' % mem
    calls.sort(key=lambda c: c['call_id'])
    refs = {x['context_id']: x
            for x in map(json.loads, open(release / 'hidden/oracle_references_v0_5_1.jsonl'))}

    cfg = json.load(open(a.config))
    ad = BedrockOpenAIAdapter(cfg)          # interlock ON: this is a real run
    print('memoria %s | %d llamadas | %d ejecuciones | modelo %s'
          % (mem, len(calls), a.runs, cfg['model']))

    runs = []
    try:
        for r in range(a.runs):
            rec = {}
            for i, call in enumerate(calls, 1):
                try:
                    resp = ad.invoke(call)
                except TransportHTTPError as e:
                    rec[call['call_id']] = {'error': 'HTTP %s' % e.code}
                    continue
                txt = resp.get('assistant_text') or ''
                pr = parse_final_answer(txt, None, resp.get('finish_reason'),
                                        True, end_m, start_m)
                row = {'sha': hashlib.sha256(txt.encode()).hexdigest()[:16],
                       'status': pr.status, 'out_tokens': resp.get('output_tokens')}
                if pr.obj is not None and not schema_errors(pr.obj):
                    row['decision'] = json.dumps(
                        {'reaction': pr.obj.get('reaction'), 'rule_id': pr.obj.get('rule_id'),
                         'ids': sorted(pr.obj.get('decisive_event_ids') or [])}, sort_keys=True)
                    sc = interpret(pr.obj, call['payload'], refs[call['context_id']],
                                   call['condition'])
                    row['reaction_correct'] = sc['reaction_correct']
                    row['rule_correct'] = sc['rule_correct']
                rec[call['call_id']] = row
                print('\r  run %d: %d/%d' % (r + 1, i, len(calls)), end='', flush=True)
            print()
            runs.append(rec)
    except BudgetExceeded as e:
        print('\n%s' % e)
        return 2

    ids = [c['call_id'] for c in calls]
    def agree(field):
        ok = [i for i in ids if all(field in r.get(i, {}) for r in runs)]
        same = [i for i in ok if len({json.dumps(r[i][field]) for r in runs}) == 1]
        return len(same), len(ok)

    b_s, b_n = agree('sha')
    d_s, d_n = agree('decision')
    accs = []
    for r in runs:
        v = [r[i]['reaction_correct'] for i in ids if 'reaction_correct' in r.get(i, {})]
        accs.append(sum(v) / len(v) if v else None)
    sc_s, sc_n = agree('reaction_correct')

    res = {'memory_id': mem, 'model': cfg['model'], 'runs': a.runs, 'calls': len(calls),
           'byte_identical': [b_s, b_n], 'decision_identical': [d_s, d_n],
           'reaction_correct_identical': [sc_s, sc_n],
           'accuracy_per_run': accs,
           'accuracy_spread_pp': (round((max(accs) - min(accs)) * 100, 2)
                                  if all(x is not None for x in accs) else None),
           'budget': ad.guard.summary()}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.config).stem
    (out / ('repeatability_%s.json' % stem)).write_text(json.dumps(res, indent=2))

    pct = lambda s, n: ('%.1f%%' % (100 * s / n)) if n else 'n/a'
    print('\n  texto identico byte a byte : %s (%d/%d)' % (pct(b_s, b_n), b_s, b_n))
    print('  decision identica          : %s (%d/%d)' % (pct(d_s, d_n), d_s, d_n))
    print('  reaction_correct identico  : %s (%d/%d)' % (pct(sc_s, sc_n), sc_s, sc_n))
    print('  accuracy por ejecucion     : %s' % ['%.4f' % x if x is not None else None for x in accs])
    print('  DESPLAZAMIENTO             : %s pp  <- el numero para el paper' % res['accuracy_spread_pp'])
    print('  gasto                      : $%.4f' % ad.guard.spent)
    print('\nescrito %s' % (out / ('repeatability_%s.json' % stem)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
