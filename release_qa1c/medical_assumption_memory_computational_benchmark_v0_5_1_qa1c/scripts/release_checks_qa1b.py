"""Annex B release checks: call matrix, split isolation, and archive hygiene.

Implements items 4 to 7 of section 11 of the Official Release and Assessment Decision
(15 August 2026). Model-free and read-only apart from its own report.

    python scripts/release_checks_qa1b.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[1]

EXPECTED = {'memories': 32, 'contexts_per_memory': 5, 'renderings': 3, 'conditions': 3,
            'calls': 1440}
SECRET_PATTERNS = [
    (re.compile(r'sk-[A-Za-z0-9]{16,}'), 'openai-style key'),
    (re.compile(r'Bearer\s+[A-Za-z0-9._\-]{20,}'), 'bearer token literal'),
    (re.compile(r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\'][^"\']{12,}["\']'),
     'inline credential'),
]
LOCAL_PATH = re.compile(r'/home/[a-z0-9_\-]+/|/Users/[A-Za-z0-9_\-]+/|C:\\\\Users\\\\')
TEXT_SUFFIX = {'.py', '.json', '.md', '.txt', '.csv', '.cfg', '.ini', '.yaml', '.yml'}

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append({'check': name, 'pass': bool(ok), 'detail': detail})
    print('  {0} {1}{2}'.format('PASS' if ok else 'FAIL', name,
                                ' :: ' + detail if detail and not ok else ''))


def main():
    calls = [json.loads(x) for x in open(R / 'prompts/model_calls_v0_5_1.jsonl')]
    split = {x['memory_id']: x['split'].upper()
             for x in csv.DictReader(open(R / 'data_v0_5_1/split_manifest.csv'))}
    ctx = {x['context_id']: x for x in csv.DictReader(open(R / 'data_v0_5_1/contexts.csv'))}

    print('4. expected reserved call matrix')
    reserved = [c for c in calls if split[c['memory_id']] == 'RESERVED']
    mems = sorted({c['memory_id'] for c in reserved})
    canon = {c['canonical_id'] for c in reserved}
    rend = Counter(ctx[c['context_id']]['render_family'] for c in reserved)
    per_mem_canon = defaultdict(set)
    for c in reserved:
        per_mem_canon[c['memory_id']].add(c['canonical_id'])
    ids = [c['call_id'] for c in reserved]

    check('32 reserved memories', len(mems) == EXPECTED['memories'], str(len(mems)))
    check('5 canonical contexts per memory',
          set(len(v) for v in per_mem_canon.values()) == {EXPECTED['contexts_per_memory']},
          str(sorted(set(len(v) for v in per_mem_canon.values()))))
    check('160 canonical contexts', len(canon) == 160, str(len(canon)))
    check('3 rendering families, evenly used', len(rend) == EXPECTED['renderings'] and
          len(set(rend.values())) == 1, json.dumps(rend))
    check('3 conditions per rendered context',
          set(Counter(c['context_id'] for c in reserved).values()) == {EXPECTED['conditions']},
          str(sorted(set(Counter(c['context_id'] for c in reserved).values()))))
    check('32 x 5 x 3 x 3 = 1,440 reserved calls',
          len(reserved) == EXPECTED['calls'], str(len(reserved)))
    check('no duplicate call ids', len(ids) == len(set(ids)),
          str(len(ids) - len(set(ids))) + ' duplicates')
    check('no omissions: every reserved context has all three conditions',
          all(len({c['condition'] for c in reserved if c['context_id'] == cid}) == 3
              for cid in {c['context_id'] for c in reserved}))

    print('5. split isolation')
    dev_mem = {m for m, s in split.items() if s == 'DEVELOPMENT'}
    check('no development memory appears in the reserved set',
          not (set(mems) & dev_mem), json.dumps(sorted(set(mems) & dev_mem)))
    check('development and reserved partition the 40 memories',
          len(dev_mem) == 8 and len(mems) == 32 and len(dev_mem | set(mems)) == 40)
    check('no reserved call id appears in the development set',
          not ({c['call_id'] for c in reserved} &
               {c['call_id'] for c in calls if split[c['memory_id']] == 'DEVELOPMENT'}))

    print('6. no reserved model response exists')
    reserved_ids = {c['call_id'] for c in reserved}
    found = []
    for p in sorted((R / 'results').rglob('*.jsonl')) if (R / 'results').exists() else []:
        for line in p.open():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('call_id') in reserved_ids:
                found.append('{0}:{1}'.format(p.relative_to(R), row.get('call_id')))
                break
    check('no reserved call_id in any results file', not found, json.dumps(found[:5]))
    evid = R / 'evidence'
    ev_found = []
    if evid.exists():
        for p in sorted(evid.rglob('*.jsonl')):
            for line in p.open():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get('call_id') in reserved_ids:
                    ev_found.append('{0}:{1}'.format(p.relative_to(R), row.get('call_id')))
                    break
    check('no reserved call_id in the live evidence captures', not ev_found,
          json.dumps(ev_found[:5]))

    print('7. archive hygiene')
    caches = [str(p.relative_to(R)) for p in R.rglob('__pycache__')]
    pyc = [str(p.relative_to(R)) for p in R.rglob('*.pyc')]
    check('no __pycache__ directories', not caches, json.dumps(caches[:5]))
    check('no .pyc files', not pyc, json.dumps(pyc[:5]))

    secrets, locals_ = [], []
    for p in sorted(R.rglob('*')):
        if not p.is_file() or p.suffix not in TEXT_SUFFIX:
            continue
        rel = p.relative_to(R).as_posix()
        try:
            text = p.read_text(errors='replace')
        except OSError:
            continue
        for rx, label in SECRET_PATTERNS:
            if rx.search(text):
                secrets.append('{0} ({1})'.format(rel, label))
                break
        if LOCAL_PATH.search(text):
            locals_.append(rel)
    check('no credential-shaped literals', not secrets, json.dumps(secrets[:5]))
    check('no absolute local paths embedded', not locals_, json.dumps(locals_[:8]))

    failed = [r['check'] for r in RESULTS if not r['pass']]
    print('\n{0}/{1} checks passed'.format(len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print('FAILED: ' + ', '.join(failed))
    out = {'suite': 'release_checks_qa1b',
           'authority': 'Official Release and Assessment Decision v0.5.1-qa1b, section 11 items 4-7',
           'reserved_matrix': {'memories': len(mems), 'canonical_contexts': len(canon),
                               'calls': len(reserved)},
           'checks': RESULTS, 'passed': len(RESULTS) - len(failed), 'total': len(RESULTS),
           'status': 'PASS' if not failed else 'FAIL'}
    (R / 'validation/release_checks_qa1b.json').write_text(json.dumps(out, indent=2))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
