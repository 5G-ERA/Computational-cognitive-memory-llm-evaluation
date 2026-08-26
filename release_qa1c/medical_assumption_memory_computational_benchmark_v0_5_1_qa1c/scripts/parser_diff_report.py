"""Differential verification of the qa1c parser against the frozen qa1b parser.

Implements the verification required by DEFECT_001 section 6 before the corrective release
may be accepted. Runs entirely offline against captured raw responses. It issues no model
call and consumes nothing.

    python tools/parser_diff_report.py --raw <path/to/responses_raw.jsonl> \
        [--scoring <path/to/scoring_records.jsonl>] [--output report.json]

Checks:
  1. Every status change is FROM COMPLETED_OUTPUT_TRUNCATED TO a scorable status.
     No record may move in any other direction.
  2. No genuinely truncated record (finish_reason == 'length') becomes scorable.
  3. Truncation rate per condition, before and after, with the section 5 bands.

Condition accuracy is deliberately NOT computed or printed. The corrective release must be
judged on extraction behaviour alone, before any outcome is inspected.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
# Resolve relative to the package so the tool is portable from any extraction root.
QA1C = HERE / 'patch/scripts/qa_core.py'
if not QA1C.exists():
    QA1C = HERE / 'scripts/qa_core.py'
SCORABLE = {'COMPLETED_VALID'}


def load(path, name):
    """Load a parser module by path under a distinct name.

    The module must be registered in sys.modules before execution: on CPython 3.8 the
    dataclass machinery resolves a class's module through sys.modules and fails otherwise.
    """
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--scoring', help='optional, to attach conditions to each call')
    ap.add_argument('--frozen', required=True,
                    help='path to the superseded parser to compare against, e.g. the qa1b qa_core.py')
    ap.add_argument('--output', default='parser_diff_report.json')
    a = ap.parse_args()

    old = load(Path(a.frozen), 'qa1b_core')
    new = load(QA1C, 'qa1c_core')
    print('frozen parser end markers : {0}'.format(old.END_MARKERS))
    print('qa1c   parser end markers : {0}'.format(new.END_MARKERS))

    cond = {}
    if a.scoring and Path(a.scoring).exists():
        for line in Path(a.scoring).open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            cond[r['call_id']] = r.get('condition')

    rows = []
    seen = set()
    for line in Path(a.raw).open():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r['call_id'] in seen:
            continue
        seen.add(r['call_id'])
        rows.append(r)

    changes, illegal, genuine_rescued = [], [], []
    before, after = Counter(), Counter()
    tr_before = defaultdict(lambda: [0, 0])
    tr_after = defaultdict(lambda: [0, 0])

    for r in rows:
        txt = r.get('assistant_text') or ''
        fr = r.get('finish_reason')
        o = old.parse_final_answer(txt, None, finish_reason=fr)
        n = new.parse_final_answer(txt, None, finish_reason=fr)
        before[o.status] += 1
        after[n.status] += 1
        c = cond.get(r['call_id'], 'UNKNOWN')
        tr_before[c][0] += 1
        tr_after[c][0] += 1
        if o.status == 'COMPLETED_OUTPUT_TRUNCATED':
            tr_before[c][1] += 1
        if n.status == 'COMPLETED_OUTPUT_TRUNCATED':
            tr_after[c][1] += 1

        if o.status != n.status:
            rec = {'call_id': r['call_id'], 'condition': c, 'finish_reason': fr,
                   'output_tokens': r.get('output_tokens'),
                   'from': o.status, 'to': n.status}
            changes.append(rec)
            if not (o.status == 'COMPLETED_OUTPUT_TRUNCATED' and n.status in SCORABLE):
                illegal.append(rec)
            if fr == 'length' and n.status in SCORABLE:
                genuine_rescued.append(rec)

    print('\nresponses inspected : {0}'.format(len(rows)))
    print('status BEFORE       : {0}'.format(json.dumps(dict(before))))
    print('status AFTER        : {0}'.format(json.dumps(dict(after))))
    print('records changed     : {0}'.format(len(changes)))

    print('\ncheck 1 — every change is truncated -> scorable')
    print('  {0}  ({1} illegal transition(s))'.format('PASS' if not illegal else 'FAIL',
                                                      len(illegal)))
    for x in illegal[:10]:
        print('    {0}: {1} -> {2}'.format(x['call_id'], x['from'], x['to']))

    print('check 2 — no finish_reason=length record becomes scorable')
    print('  {0}  ({1} wrongly rescued)'.format('PASS' if not genuine_rescued else 'FAIL',
                                                len(genuine_rescued)))
    for x in genuine_rescued[:10]:
        print('    {0}: {1} tokens'.format(x['call_id'], x['output_tokens']))

    print('\ncheck 3 — truncation rate per condition')
    print('  {0:<24} {1:>18} {2:>18}'.format('condition', 'before', 'after'))
    for c in sorted(tr_before):
        b = tr_before[c]
        f = tr_after[c]
        print('  {0:<24} {1:>7}/{2:<4} {3:>5.2f}% {4:>7}/{5:<4} {6:>5.2f}%'.format(
            c, b[1], b[0], 100.0 * b[1] / b[0], f[1], f[0], 100.0 * f[1] / f[0]))
    tb = sum(v[1] for v in tr_before.values())
    ta = sum(v[1] for v in tr_after.values())
    tot = sum(v[0] for v in tr_before.values())
    print('  {0:<24} {1:>7}/{2:<4} {3:>5.2f}% {4:>7}/{5:<4} {6:>5.2f}%'.format(
        'POOLED', tb, tot, 100.0 * tb / tot, ta, tot, 100.0 * ta / tot))
    rates = [v[1] / v[0] for c, v in tr_after.items() if c != 'UNKNOWN' and v[0]]
    spread = (max(rates) - min(rates)) if len(rates) > 1 else 0.0
    print('  between-arm spread after : {0:.2f}%  [{1}]'.format(
        100 * spread, 'STOP' if spread > .10 else ('WARN' if spread > .05 else 'ok')))

    status = 'PASS' if not illegal and not genuine_rescued else 'FAIL'
    print('\nVERIFICATION: {0}'.format(status))
    print('Condition accuracy was not computed. The corrective release is judged on '
          'extraction behaviour only.')

    out = {
        'report': 'qa1c_parser_diff',
        'defect': 'DEFECT_001 malformed reasoning end marker',
        'responses_inspected': len(rows),
        'frozen_end_markers': list(old.END_MARKERS),
        'qa1c_end_markers': list(new.END_MARKERS),
        'status_before': dict(before),
        'status_after': dict(after),
        'records_changed': len(changes),
        'changes': changes,
        'check_1_only_truncated_to_scorable': not illegal,
        'illegal_transitions': illegal,
        'check_2_no_genuine_truncation_rescued': not genuine_rescued,
        'wrongly_rescued': genuine_rescued,
        'truncation_by_condition_before': {c: v for c, v in tr_before.items()},
        'truncation_by_condition_after': {c: v for c, v in tr_after.items()},
        'between_arm_spread_after': round(spread, 6),
        'condition_accuracy_computed': False,
        'status': status,
    }
    Path(a.output).write_text(json.dumps(out, indent=2))
    print('written {0}'.format(a.output))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
