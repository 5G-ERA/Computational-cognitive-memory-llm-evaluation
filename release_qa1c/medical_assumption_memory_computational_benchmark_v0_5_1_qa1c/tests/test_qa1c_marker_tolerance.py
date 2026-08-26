"""qa1c regression suite: tolerant end marker, and everything it must NOT change.

    python tests/test_qa1c_marker_tolerance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Runs from the overlay layout (patch/scripts) and from a package the patch was applied to.
BASE = ROOT / 'patch' if (ROOT / 'patch/scripts/qa_core.py').exists() else ROOT
sys.path.insert(0, str(BASE / 'scripts'))

from qa_core import END_MARKERS, parse_final_answer  # noqa: E402

FINAL = ('{"reaction":"CONTINUE_SUPPORT","rule_id":"R10_CONFIRMED_CONTINUATION",'
         '"decisive_event_ids":["EVT-0000002"],"reason":"resolved"}')
DRAFT = '{"reaction":"TAILOR_SUPPORT","note":"draft I will discard"}'

RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond)))
    print('  {0} {1}{2}'.format('PASS' if cond else 'FAIL', name,
                                ' :: ' + detail if detail and not cond else ''))


def main():
    print('1. the tolerant marker recovers what the frozen parser discarded')
    malformed = '◁think▷ deliberating ' + DRAFT + ' on reflection no ◁/think\n\n```json\n' + FINAL + '\n```'
    r = parse_final_answer(malformed, None, finish_reason='stop')
    check('malformed end marker yields a scorable result', r.status == 'COMPLETED_VALID', r.status)
    check('the final object is taken, not the draft',
          r.obj and r.obj['reaction'] == 'CONTINUE_SUPPORT', str(r.obj))
    check('code fences around the final object are tolerated', r.obj is not None)

    print('2. the well-formed marker still wins where both could match')
    wellformed = '◁think▷ deliberating ' + DRAFT + ' ◁/think▷\n' + FINAL
    r = parse_final_answer(wellformed, None, finish_reason='stop')
    check('well-formed marker still parses', r.status == 'COMPLETED_VALID', r.status)
    check('no stray marker glyph leaks into the parsed object',
          r.obj and set(r.obj) == {'reaction', 'rule_id', 'decisive_event_ids', 'reason'},
          str(r.obj))
    check('tolerant form is listed after the well-formed form',
          END_MARKERS.index('◁/think▷') < END_MARKERS.index('◁/think'))

    print('3. genuine truncation is STILL truncation — the fix must not rescue it')
    r = parse_final_answer('◁think▷ reasoning that never ends', None, finish_reason='length')
    check('finish_reason=length stays truncated', r.status == 'COMPLETED_OUTPUT_TRUNCATED', r.status)
    r = parse_final_answer('◁think▷ reasoning ◁/think\n' + FINAL, None, finish_reason='length')
    check('length wins over a recovered marker',
          r.status == 'COMPLETED_OUTPUT_TRUNCATED', r.status)
    r = parse_final_answer('◁think▷ reasoning with no end at all', None, finish_reason='stop')
    check('unclosed block with no end marker stays truncated',
          r.status == 'COMPLETED_OUTPUT_TRUNCATED', r.status)

    print('4. every other frozen rule is unchanged')
    r = parse_final_answer(FINAL, None, finish_reason='stop')
    check('marker-less complete message still parses on its merits',
          r.status == 'COMPLETED_VALID', r.status)
    r = parse_final_answer('◁think▷ x ◁/think\n' + FINAL + '\n' + FINAL, None, finish_reason='stop')
    check('two final objects are still invalid', r.status == 'COMPLETED_INVALID_JSON', r.status)
    r = parse_final_answer('◁think▷ x ◁/think\nno object here', None, finish_reason='stop')
    check('no final object is still invalid JSON', r.status == 'COMPLETED_INVALID_JSON', r.status)
    r = parse_final_answer('', None, finish_reason='stop')
    check('empty output is still MODEL_EMPTY', r.status == 'MODEL_EMPTY', r.status)
    r = parse_final_answer('anything', {'reaction': 'X'}, finish_reason='stop')
    check('a provider structured object still short-circuits', r.status == 'COMPLETED_VALID')

    print('5. the HTML-style markers are untouched')
    r = parse_final_answer('<think> x </think>\n' + FINAL, None, finish_reason='stop')
    check('</think> still parses', r.status == 'COMPLETED_VALID', r.status)
    check('no bare </think variant was introduced', '</think' not in END_MARKERS)

    failed = [n for n, ok in RESULTS if not ok]
    print('\n{0}/{1} checks passed'.format(len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print('FAILED: ' + ', '.join(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
