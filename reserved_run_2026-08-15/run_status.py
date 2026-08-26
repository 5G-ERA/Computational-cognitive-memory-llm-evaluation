"""Status and section-5 operational monitoring for the reserved run.

Read-only. Lives OUTSIDE the frozen package so the release archive is untouched.
Reports progress and the operational thresholds frozen in the release decision:

    overall output truncation                        warn 5%    stop 10%
    absolute truncation difference between arms      warn 5pp   stop 10pp
    invalid-output rate                              warn 5%    stop 10%

It deliberately does NOT print condition accuracy: the decision requires that a stop
threshold pauses execution *before* condition-accuracy results are inspected.

    python run_status.py [--accuracy]   # --accuracy only after the run is complete
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

RUN = Path(__file__).resolve().parent / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1b' / 'results/reserved_2026-08-15'
EXPECTED = 1440
TRUNC = {'COMPLETED_OUTPUT_TRUNCATED'}
INVALID = {'COMPLETED_INVALID_JSON', 'COMPLETED_INVALID_SCHEMA', 'MODEL_EMPTY'}


MIN_N = 200  # Restart decision 001: bands carry no stop authority below this denominator.


def band(value, warn, stop, n=None):
    """Section 5 operational band, evaluated only from MIN_N terminal records.

    The thresholds are stated as rates with no minimum denominator, so at small n a single
    event reaches the stop band while the rate estimate carries no information. Below MIN_N
    the value is reported but marked not-yet-evaluable.
    """
    if n is not None and n < MIN_N:
        return 'n<{0}'.format(MIN_N)
    if value > stop:
        return 'STOP'
    if value > warn:
        return 'WARN'
    return 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--accuracy', action='store_true',
                    help='print condition accuracy; only permitted once the run is complete')
    a = ap.parse_args()

    recs = []
    p = RUN / 'scoring_records.jsonl'
    if p.exists():
        for line in p.open():
            try:
                recs.append(json.loads(line))
            except ValueError:
                pass
    done = len(recs)
    print('progress            : {0}/{1} ({2:.1f}%)'.format(done, EXPECTED, 100.0 * done / EXPECTED))
    if not done:
        print('no terminal records yet')
        return 0

    st = Counter(r['status'] for r in recs)
    print('statuses            : ' + json.dumps(dict(st)))

    # Defect 001: a malformed end marker ("◁/think" without "▷") is scored
    # COMPLETED_OUTPUT_TRUNCATED although the reply completed normally. Report the frozen
    # classification AND the genuine-truncation rate, so a spurious stop is visible as such
    # without quietly weakening the frozen threshold.
    genuine = malformed = 0
    raw_p = RUN / 'responses_raw.jsonl'
    if raw_p.exists():
        fr = {}
        for line in raw_p.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            fr[r.get('call_id')] = r
        for r in recs:
            if r['status'] != 'COMPLETED_OUTPUT_TRUNCATED':
                continue
            rr = fr.get(r['call_id'], {})
            if rr.get('finish_reason') == 'length':
                genuine += 1
            elif '◁/think' in (rr.get('assistant_text') or ''):
                malformed += 1
            else:
                genuine += 1

    trunc = sum(st.get(k, 0) for k in TRUNC)
    inval = sum(st.get(k, 0) for k in INVALID)
    tr = trunc / done
    ir = inval / done
    print('truncation rate     : {0:.3%}  [{1}]   (frozen classification)'.format(
        tr, band(tr, .05, .10, done)))
    if malformed:
        gr = genuine / done
        print('  genuine truncation: {0:.3%}  [{1}]   ({2} at ceiling)'.format(
            gr, band(gr, .05, .10, done), genuine))
        print('  malformed marker  : {0} call(s) — defect 001, valid answers wrongly '
              'classified'.format(malformed))
    print('invalid-output rate : {0:.3%}  [{1}]'.format(ir, band(ir, .05, .10, done)))

    by = defaultdict(lambda: [0, 0])
    for r in recs:
        by[r['condition']][0] += 1
        if r['status'] in TRUNC:
            by[r['condition']][1] += 1
    rates = {c: (v[1] / v[0] if v[0] else 0.0) for c, v in sorted(by.items())}
    for c, v in sorted(by.items()):
        print('  {0:<22} n={1:<5} truncated={2} ({3:.2%})'.format(c, v[0], v[1], rates[c]))
    if len(rates) > 1:
        spread = max(rates.values()) - min(rates.values())
        print('arm truncation spread: {0:.3%}  [{1}]'.format(spread, band(spread, .05, .10, done)))

    attempts = RUN / 'attempts.jsonl'
    if attempts.exists():
        rows = [json.loads(x) for x in attempts.open()]
        retried = sum(1 for r in rows if r.get('outcome') == 'RETRYABLE_ERROR')
        restart = sum(1 for r in rows if r.get('restartable'))
        print('retryable attempts  : {0}   awaiting restart: {1}'.format(retried, restart))

    if a.accuracy:
        if done < EXPECTED:
            print('\nREFUSED: condition accuracy is withheld until the run is complete '
                  '({0}/{1}).'.format(done, EXPECTED))
            return 2
        ok = [r for r in recs if r['status'] == 'COMPLETED_VALID']
        print('\nintention-to-evaluate accuracy (every expected call in the denominator):')
        for c in sorted(by):
            n = by[c][0]
            correct = sum(1 for r in ok if r['condition'] == c and r.get('reaction_correct'))
            print('  {0:<22} {1:.4f}  ({2}/{3})'.format(c, correct / n, correct, n))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
