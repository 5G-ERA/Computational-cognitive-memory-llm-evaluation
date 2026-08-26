#!/usr/bin/env python3
"""Frozen section 6 analysis applied to a Bedrock development-split arm.

The estimator is NOT reimplemented here. Everything statistical is imported from
the signed `analysis_section6.py` that produced the sealed KIMI2 reserved result:
memory-clustered bootstrap, 10,000 replicates, percentile 95% interval, seed
13082654, intention-to-evaluate denominator, and the hierarchy B1-B0 first, then
B1-M0 only if the primary succeeds, then M0-B0 as exploratory.

This file adds two things and nothing else:

  1. a loader for the DEVELOPMENT split of a Bedrock run directory;
  2. a seal.

SEAL. Under Decision 1 of the cross-model replication amendment (19 Aug 2026),
Qwen3 is the primary cross-model replication arm and its development scientific
contrasts must not be inspected before the pre-execution amendment record carries
a dated signature. Runs listed in SEALED_RUNS therefore refuse to analyse without
--signature carrying the record digest.

Terra is not sealed: its development contrasts were inspected on 19 August before
the amendment existed, and that prior inspection is disclosed in item 00 of the
record. Running Terra here re-derives numbers already on the record.

    python3 analysis_dev_arm.py --run out/dev_terra --arm terra
    python3 analysis_dev_arm.py --run out/dev_qwen3 --arm qwen3 --signature <record-sha256>
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PACKAGE = (HERE.parent / 'release_qa1c'
           / 'medical_assumption_memory_computational_benchmark_v0_5_1_qa1c')
FROZEN_ANALYSIS = Path('/home/ros/Downloads/deliverable 2/analysis/analysis_section6.py')

# Record digest of EDCA_preexecution_amendment_record_2026-08-19.html, the document
# whose signature releases the seal. Kept in RECORD_SHA256.txt beside this file.
RECORD_SHA256 = 'c8c548554da689843065d68527fe858651f00c491b4d9854aa1b17c1a3dc7ef2'

# Development runs released by the signature on the record above.
SEALED_RUNS = {'dev_qwen3'}

# Reserved runs are NOT releasable by that signature. The delegated signature of
# 19 August 2026 states explicitly: "not_released: The RESERVED split of any arm."
# No digest unlocks these; a separate authorisation record has to exist first, and
# it does not. The refusal is unconditional by design.
RESERVED_RUNS = {'reserved_qwen3', 'reserved_terra', 'reserved_qwen3_repeat'}

# A reserved run opens only when a signed inspection authorisation naming it exists.
# Deleting an entry from RESERVED_RUNS would open it with no audit trail; this way the
# seal is released by a record that says who released it and on whose instruction.
RESERVED_RELEASE = {
    'reserved_qwen3': 'signature/SIGNED_delegated_reserved_inspection.json',
    'reserved_terra': 'signature/SIGNED_delegated_terra_reserved_inspection.json',
    'reserved_qwen3_repeat': 'signature/SIGNED_delegated_reserved_repeat.json',
}


def load_frozen():
    """Import the signed analysis module without copying any of its statistics."""
    spec = importlib.util.spec_from_file_location('frozen_section6', FROZEN_ANALYSIS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_split(run_dir, split='development'):
    run = Path(run_dir)
    sys.path.insert(0, str(PACKAGE / 'scripts'))
    from qa_core import parse_final_answer                     # noqa: E402
    from core import schema_errors, interpret                  # noqa: E402

    raw = {}
    for line in (run / 'responses_raw.jsonl').open():
        r = json.loads(line)
        raw[r['call_id']] = r                                  # last attempt wins

    refs = {x['context_id']: x for x in
            (json.loads(l) for l in
             (PACKAGE / 'hidden/oracle_references_v0_5_1.jsonl').open())}
    splits = {x['memory_id']: x['split'].lower()
             for x in csv.DictReader((PACKAGE / 'data_v0_5_1/split_manifest.csv').open())}

    rows = []
    for line in (PACKAGE / 'prompts/model_calls_v0_5_1.jsonl').open():
        call = json.loads(line)
        if splits[call['memory_id']] != split:
            continue
        cid = call['call_id']
        r = raw.get(cid)
        rec = {'call_id': cid, 'memory_id': call['memory_id'],
               'context_id': call['context_id'], 'condition': call['condition'],
               'reaction_correct': 0, 'rule_correct': 0, 'status': 'MISSING'}
        if r is not None:
            pr = parse_final_answer(r.get('assistant_text') or '', None,
                                    finish_reason=r.get('finish_reason'))
            rec['status'] = pr.status
            if pr.status == 'COMPLETED_VALID' and isinstance(pr.obj, dict):
                if schema_errors(pr.obj):
                    rec['status'] = 'COMPLETED_INVALID_SCHEMA'
                else:
                    legacy = interpret(pr.obj, call['payload'],
                                       refs[call['context_id']], call['condition'])
                    consistent = legacy.get('reaction_rule_consistent', False)
                    rec['reaction_correct'] = int(bool(legacy['reaction_correct'])
                                                  and consistent)
                    rec['rule_correct'] = int(bool(legacy['rule_correct']))
        rows.append(rec)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--arm', required=True)
    ap.add_argument('--signature', help='SHA-256 of the SIGNED pre-execution amendment record')
    ap.add_argument('--output')
    a = ap.parse_args()

    run_name = Path(a.run).name
    if run_name in RESERVED_RUNS:
        relpath = RESERVED_RELEASE.get(run_name)
        rel = HERE / relpath if relpath else None
        if rel is None or not rel.exists():
            print('REFUSED. %s is a RESERVED split and no signed inspection' % run_name)
            print('authorisation naming it exists. No --signature value unlocks it.')
            return 3
        rec = json.loads(rel.read_text())
        if rec.get('covers_run') != a.run.rstrip('/'):
            print('REFUSED. %s does not name %s.' % (rel.name, a.run))
            return 3
        sig = rec['signature']
        print('SEAL RELEASED by %s' % rel.name)
        print('  signed_by      : %s' % sig['signed_by'])
        print('  capacity       : %s' % sig['capacity'])
        print('  on behalf of   : %s' % sig['on_behalf_of'])
        print('  date           : %s' % sig['date'])
        print('  owner\'s own signature: %s' % ('yes' if rec.get('is_owner_countersignature') else 'NO, delegated'))
        print()

    if Path(a.run).name in SEALED_RUNS:
        given = (a.signature or '').strip().lower()
        if given != RECORD_SHA256:
            print('REFUSED. %s is sealed under Decision 1 of the cross-model '
                  'replication amendment.' % Path(a.run).name)
            print('The pre-execution amendment record must carry a dated signature '
                  'before this arm\'s development contrasts are inspected.')
            print('Re-run with --signature %s once it does.' % RECORD_SHA256)
            return 2

    frozen = load_frozen()
    rows = load_split(a.run, 'reserved' if run_name in RESERVED_RUNS else 'development')

    by_ctx = defaultdict(dict)
    for r in rows:
        by_ctx[r['context_id']][r['condition']] = r
    ctxs = sorted(by_ctx)
    conds = sorted({r['condition'] for r in rows})
    memories = np.array([by_ctx[c][conds[0]]['memory_id'] for c in ctxs])
    correct = {cd: np.array([by_ctx[c][cd]['reaction_correct'] for c in ctxs], dtype=float)
               for cd in conds}
    rule = {cd: np.array([by_ctx[c][cd]['rule_correct'] for c in ctxs], dtype=float)
            for cd in conds}

    res = frozen.run_hierarchy(correct, memories)
    res['arm'] = a.arm
    res['split'] = 'reserved' if run_name in RESERVED_RUNS else 'development'
    res['denominator'] = 'intention-to-evaluate'
    res['estimator_source'] = str(FROZEN_ANALYSIS)
    res['calls'] = len(rows)
    res['contexts'] = len(ctxs)
    res['memories'] = int(len(set(memories.tolist())))
    res['accuracy'] = {cd: round(float(correct[cd].mean()), 6) for cd in conds}
    res['meta_decision_rule_accuracy'] = {cd: round(float(rule[cd].mean()), 6) for cd in conds}
    res['status_distribution'] = {}
    for r in rows:
        res['status_distribution'][r['status']] = \
            res['status_distribution'].get(r['status'], 0) + 1

    out = a.output or ('out/analysis_%s.json' % a.arm)
    Path(out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
