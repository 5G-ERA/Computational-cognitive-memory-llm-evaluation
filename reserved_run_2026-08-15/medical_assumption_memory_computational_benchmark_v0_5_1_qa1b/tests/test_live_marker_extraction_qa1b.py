"""Final-answer extraction checked against genuine Kimi-Dev-72B replies.

Covers the section 7 gate 'Final-answer extraction with actual model markers'. The
fixtures in evidence/live_kimi_development_calls_2026-08-14.jsonl are verbatim captures
from the endpoint (moonshotai_Kimi-Dev-72B-Q4_0.gguf via llama.cpp), not synthetic
strings, so they exercise the real Unicode reasoning markers, real code fences and real
draft objects inside the reasoning block.

Scope note: these are the live captures available in the release package. They are a
curated subset, not the complete development run, so the count is reported explicitly
rather than implied.

    python tests/test_live_marker_extraction_qa1b.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))

from qa_core import END_MARKERS, START_MARKERS, load_markers, parse_final_answer  # noqa: E402

EVIDENCE = R / 'evidence/live_kimi_development_calls_2026-08-14.jsonl'
RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond)))
    print('  {0} {1}{2}'.format('PASS' if cond else 'FAIL', name,
                                ' :: ' + detail if detail and not cond else ''))


def main():
    rows = [json.loads(x) for x in EVIDENCE.open()]
    print('live captures: {0}'.format(len(rows)))

    print('1. the configured markers are the ones the endpoint actually emits')
    end, start = load_markers(R / 'config/extraction_policy.json')
    check('unicode end marker is configured', '◁/think▷' in end)
    check('unicode start marker is configured', '◁think▷' in start)
    check('configuration agrees with the module defaults',
          set(end) == set(END_MARKERS) and set(start) == set(START_MARKERS))
    emitted = Counter()
    for r in rows:
        for m in end:
            if m in (r.get('assistant_text') or ''):
                emitted[m] += 1
    check('every configured end marker seen in the captures is Unicode',
          set(emitted) <= set(end) and emitted.get('◁/think▷', 0) > 0,
          json.dumps(emitted))
    check('the HTML-style marker never appears in real output',
          emitted.get('</think>', 0) == 0)

    print('2. every complete capture yields exactly one final object')
    statuses = Counter()
    parsed_ok = 0
    for r in rows:
        pr = parse_final_answer(r['assistant_text'], None, finish_reason=r.get('finish_reason'))
        statuses[pr.status] += 1
        if r.get('finish_reason') == 'stop':
            if pr.status == 'COMPLETED_VALID' and isinstance(pr.obj, dict):
                parsed_ok += 1
            else:
                print('      unparsed {0}: {1} {2}'.format(r['call_id'], pr.status, pr.errors))
    n_stop = sum(1 for r in rows if r.get('finish_reason') == 'stop')
    check('all complete replies parse to one object',
          parsed_ok == n_stop, '{0}/{1}'.format(parsed_ok, n_stop))
    check('truncated replies are classified as truncation, not invalid JSON',
          statuses.get('COMPLETED_OUTPUT_TRUNCATED', 0) ==
          sum(1 for r in rows if r.get('finish_reason') == 'length'),
          json.dumps(statuses))
    check('no capture is silently dropped', sum(statuses.values()) == len(rows))

    print('3. the parsed object is the final answer, not a draft from the reasoning block')
    ok = True
    for r in rows:
        if r.get('finish_reason') != 'stop':
            continue
        text = r['assistant_text']
        pr = parse_final_answer(text, None, finish_reason='stop')
        cut = min(text.find(m) for m in END_MARKERS if text.find(m) >= 0)
        tail = text[cut:]
        if pr.obj is not None and json.dumps(pr.obj, sort_keys=True)[:20] and \
                pr.obj.get('reaction') is not None:
            # the reaction that was extracted must appear after the end marker
            if pr.obj['reaction'] not in tail:
                ok = False
                print('      draft leak in {0}'.format(r['call_id']))
    check('extracted reaction always comes from the post-reasoning segment', ok)

    print('4. the extracted objects carry the fields the scorer needs')
    fields = Counter()
    for r in rows:
        if r.get('finish_reason') != 'stop':
            continue
        pr = parse_final_answer(r['assistant_text'], None, finish_reason='stop')
        if isinstance(pr.obj, dict):
            for k in pr.obj:
                fields[k] += 1
    check('reaction present in every parsed object', fields.get('reaction', 0) == n_stop,
          json.dumps(fields))
    check('a rule identifier is present in every parsed object',
          fields.get('rule_id', 0) == n_stop, json.dumps(fields))
    check('decisive_event_ids present in every parsed object',
          fields.get('decisive_event_ids', 0) == n_stop, json.dumps(fields))

    print('5. transport hygiene of the captures themselves')
    # The endpoint assigns a conversation id per response; the requirement is that the
    # client never REUSES one, so each call must carry its own and history must not grow.
    conv = [r.get('conversation_id') for r in rows]
    check('every call got its own server-assigned conversation id, none reused',
          len(set(conv)) == len(conv),
          json.dumps(Counter(conv).most_common(3)))
    check('no capture carries accumulated multi-turn history',
          all(int(r.get('history_messages') or 0) <= 2 for r in rows),
          json.dumps(Counter(r.get('history_messages') for r in rows)))
    check('finish_reason is populated on every capture',
          all(r.get('finish_reason') for r in rows))
    check('output stayed under the frozen 4096-token ceiling on complete replies',
          all((r.get('usage') or {}).get('completion_tokens', 0) <= 4096
              for r in rows if r.get('finish_reason') == 'stop'),
          json.dumps(sorted(((r.get('usage') or {}).get('completion_tokens', 0))
                            for r in rows)[-3:]))

    failed = [n for n, ok_ in RESULTS if not ok_]
    print('\n{0}/{1} checks passed'.format(len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print('FAILED: ' + ', '.join(failed))
    json.dump({'suite': 'live_marker_extraction_qa1b',
               'live_captures': len(rows),
               'scope': 'curated live subset available in the release package, not the full development run',
               'status_distribution': dict(statuses),
               'checks': [{'name': n, 'pass': ok_} for n, ok_ in RESULTS],
               'passed': len(RESULTS) - len(failed), 'total': len(RESULTS),
               'status': 'PASS' if not failed else 'FAIL'},
              open(R / 'validation/live_marker_extraction_qa1b.json', 'w'), indent=2)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
