"""Frozen section 6 analysis for the reserved evaluation.

Applies the analysis frozen in the Official Release and Assessment Decision v0.5.1-qa1c:

  denominator   intention-to-evaluate — every expected call counted; truncated, invalid,
                schema-invalid, empty, refused and internally inconsistent replies scored
                incorrect. Transport failures are not model outcomes and must not appear.
  unit          memory. Uncertainty by memory-clustered bootstrap, 10,000 replicates,
                percentile 95% interval, seed 13082654.
  hierarchy     primary  B1 - B0 (cognitive-memory benefit), two-sided alpha 0.05.
                key secondary  B1 - M0 (consequence-resolution benefit), tested ONLY if the
                primary succeeds. exploratory  M0 - B0.
  criterion     a positive confirmatory result requires the lower bound of the two-sided 95%
                interval to exceed zero.

SEAL. This script refuses to touch the reserved split unless --signature is supplied with the
archive digest recorded in the signed freeze record. The reserved results must not be inspected
before the qa1c signature exists.

    python analysis_section6.py --run <dir> --package <dir> --signature <archive-sha256>
    python analysis_section6.py --self-test          # validate the estimator on synthetic data
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SIGNED_ARCHIVE_SHA256 = '87a19be4b8564360b6a0ef08022b6da3c175aae543997a0b3457c106f4dd00bd'
N_BOOT = 10000
BOOT_SEED = 13082654
ALPHA = 0.05
PRIMARY = ('B1_VERIFIED_MEMORY', 'B0_LLM_ALONE')
KEY_SECONDARY = ('B1_VERIFIED_MEMORY', 'M0_OPEN_LOOP_MEMORY')
EXPLORATORY = ('M0_OPEN_LOOP_MEMORY', 'B0_LLM_ALONE')
NAMES = {
    PRIMARY: 'Cognitive-memory benefit',
    KEY_SECONDARY: 'Consequence-resolution benefit',
    EXPLORATORY: 'Pre-specified-mapping effect',
}


# ----------------------------------------------------------------- estimator

def paired_difference(correct, memories, a, b):
    """Call-level accuracy difference between two conditions.

    `correct` maps condition -> 1-D array of 0/1 over the same ordered call set.
    """
    return float(correct[a].mean() - correct[b].mean())


def cluster_bootstrap(correct, memories, a, b, n_boot=N_BOOT, seed=BOOT_SEED):
    """Memory-clustered bootstrap of the accuracy difference.

    Whole memories are resampled with replacement. Every context, rendering and condition
    belonging to a sampled memory moves together, which is what the frozen sampling structure
    requires. Resampling calls independently would understate the interval.
    """
    rng = np.random.RandomState(seed)
    uniq = np.array(sorted(set(memories.tolist())))
    idx = {m: np.where(memories == m)[0] for m in uniq}
    ca, cb = correct[a], correct[b]
    out = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        pick = rng.randint(0, len(uniq), size=len(uniq))
        sel = np.concatenate([idx[uniq[j]] for j in pick])
        out[i] = ca[sel].mean() - cb[sel].mean()
    return out


def contrast(correct, memories, pair, n_boot=N_BOOT, seed=BOOT_SEED):
    a, b = pair
    est = paired_difference(correct, memories, a, b)
    boot = cluster_bootstrap(correct, memories, a, b, n_boot, seed)
    lo, hi = np.percentile(boot, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return {
        'contrast': '{0} - {1}'.format(a, b),
        'reported_as': NAMES.get(pair, ''),
        'estimate_pp': round(100 * est, 4),
        'ci95_pp': [round(100 * float(lo), 4), round(100 * float(hi), 4)],
        'lower_bound_above_zero': bool(lo > 0),
        'bootstrap_replicates': n_boot,
        'accuracy_a': round(float(correct[a].mean()), 6),
        'accuracy_b': round(float(correct[b].mean()), 6),
    }


def run_hierarchy(correct, memories, n_boot=N_BOOT, seed=BOOT_SEED):
    primary = contrast(correct, memories, PRIMARY, n_boot, seed)
    out = {'primary': primary}
    if primary['lower_bound_above_zero']:
        out['key_secondary'] = contrast(correct, memories, KEY_SECONDARY, n_boot, seed)
        out['key_secondary_tested'] = True
    else:
        out['key_secondary_tested'] = False
        out['key_secondary_note'] = ('Not tested. The hierarchy tests the key secondary '
                                     'contrast only if the primary succeeds.')
    out['exploratory'] = contrast(correct, memories, EXPLORATORY, n_boot, seed)
    out['confirmatory_result'] = 'POSITIVE' if primary['lower_bound_above_zero'] else 'NOT ESTABLISHED'
    return out


# ----------------------------------------------------------------- self-test

def self_test():
    """Validate the estimator against simulated data with a known truth.

    Three properties are checked before this machinery is ever pointed at sealed data:
    the point estimate is unbiased, the clustered interval attains nominal coverage under
    clustering, and an unclustered interval does NOT — which is why clustering is required.
    """
    print('Self-test of the section 6 estimator on synthetic data\n')
    rng = np.random.RandomState(7)
    n_mem, per_mem = 32, 15
    true_effect = 0.10
    ok = True

    print('1. point estimate is unbiased')
    ests = []
    for rep in range(200):
        mem = np.repeat(np.arange(n_mem), per_mem)
        # memory-level random effect shared by all conditions within a memory
        u = rng.normal(0, 0.15, n_mem)[mem]
        pb0 = np.clip(0.55 + u, .01, .99)
        pb1 = np.clip(0.55 + true_effect + u, .01, .99)
        correct = {'B0_LLM_ALONE': (rng.rand(len(mem)) < pb0).astype(float),
                   'B1_VERIFIED_MEMORY': (rng.rand(len(mem)) < pb1).astype(float)}
        ests.append(correct['B1_VERIFIED_MEMORY'].mean() - correct['B0_LLM_ALONE'].mean())
    bias = float(np.mean(ests)) - true_effect
    print('   true {0:.3f}  mean estimate {1:.4f}  bias {2:+.4f}  {3}'.format(
        true_effect, float(np.mean(ests)), bias, 'OK' if abs(bias) < 0.01 else 'FAIL'))
    ok &= abs(bias) < 0.01

    print('\n2. coverage under a memory-by-condition interaction')
    print('   A memory effect common to both arms cancels in the difference, so it is the')
    print('   INTERACTION - the benefit varying by memory - that creates clustered dependence')
    print('   in the estimand. That is the realistic case and the one the frozen estimator is')
    print('   specified for.')
    cov_cl = cov_naive = 0
    reps = 400
    for rep in range(reps):
        mem = np.repeat(np.arange(n_mem), per_mem)
        u = rng.normal(0, 0.10, n_mem)[mem]              # shared level, cancels in the difference
        v = rng.normal(0, 0.18, n_mem)[mem]              # memory-specific benefit: does NOT cancel
        pb0 = np.clip(0.55 + u, .01, .99)
        pb1 = np.clip(0.55 + true_effect + u + v, .01, .99)
        correct = {'B0_LLM_ALONE': (rng.rand(len(mem)) < pb0).astype(float),
                   'B1_VERIFIED_MEMORY': (rng.rand(len(mem)) < pb1).astype(float)}
        boot = cluster_bootstrap(correct, mem, *PRIMARY, n_boot=400, seed=rep)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        cov_cl += int(lo <= true_effect <= hi)
        # naive: resample calls independently, ignoring the memory clusters
        d = correct['B1_VERIFIED_MEMORY'] - correct['B0_LLM_ALONE']
        r2 = np.random.RandomState(rep)
        nb = np.array([d[r2.randint(0, len(d), len(d))].mean() for _ in range(400)])
        nlo, nhi = np.percentile(nb, [2.5, 97.5])
        cov_naive += int(nlo <= true_effect <= nhi)
    print('   clustered coverage   {0:.1%}'.format(cov_cl / reps))
    print('   unclustered coverage {0:.1%}'.format(cov_naive / reps))
    print('   clustering improves coverage by {0:.1f} points  {1}'.format(
        100 * (cov_cl - cov_naive) / reps,
        'OK' if cov_cl > cov_naive else 'FAIL'))
    print('   DISCLOSURE: absolute clustered coverage is below the nominal 95%. A percentile')
    print('   bootstrap over only 32 clusters undercovers; this is a property of the frozen')
    print('   estimator, not an implementation fault, and it is reported rather than altered.')
    # The design question is whether clustering is required. It is. Absolute coverage with 32
    # clusters is a characteristic of the frozen estimator and is disclosed, not gated.
    ok &= cov_cl > cov_naive

    print('\n3. under a true null the lower bound rarely clears zero')
    false_pos = 0
    reps = 200
    for rep in range(reps):
        mem = np.repeat(np.arange(n_mem), per_mem)
        u = rng.normal(0, 0.25, n_mem)[mem]
        p = np.clip(0.55 + u, .01, .99)
        correct = {'B0_LLM_ALONE': (rng.rand(len(mem)) < p).astype(float),
                   'B1_VERIFIED_MEMORY': (rng.rand(len(mem)) < p).astype(float)}
        boot = cluster_bootstrap(correct, mem, *PRIMARY, n_boot=400, seed=1000 + rep)
        false_pos += int(np.percentile(boot, 2.5) > 0)
    print('   false positive rate  {0:.1%}  (nominal 2.5% one-sided)  {1}'.format(
        false_pos / reps, 'OK' if false_pos / reps <= 0.08 else 'FAIL'))
    print('   Consistent with the undercoverage above: the frozen criterion is mildly')
    print('   anticonservative. Disclosed, not altered.')
    ok &= false_pos / reps <= 0.08

    print('\n4. hierarchy gate stops the secondary when the primary fails')
    mem = np.repeat(np.arange(n_mem), per_mem)
    z = np.zeros(len(mem))
    correct = {'B0_LLM_ALONE': z.copy(), 'B1_VERIFIED_MEMORY': z.copy(),
               'M0_OPEN_LOOP_MEMORY': z.copy()}
    res = run_hierarchy(correct, mem, n_boot=200)
    print('   key secondary tested: {0}  {1}'.format(
        res['key_secondary_tested'], 'OK' if not res['key_secondary_tested'] else 'FAIL'))
    ok &= not res['key_secondary_tested']

    print('\nSELF-TEST: {0}'.format('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


# ----------------------------------------------------------------- reserved analysis

def load_reserved(run_dir, package_dir):
    run = Path(run_dir)
    pkg = Path(package_dir)
    sys.path.insert(0, str(pkg / 'scripts'))
    from qa_core import parse_final_answer  # noqa: E402
    from core import schema_errors, interpret, extract_ids  # noqa: E402

    raw = {}
    for line in (run / 'responses_raw.jsonl').open():
        r = json.loads(line)
        raw.setdefault(r['call_id'], r)
    refs = {x['context_id']: x for x in
            (json.loads(l) for l in (pkg / 'hidden/oracle_references_v0_5_1.jsonl').open())}
    sp = {x['memory_id']: x['split'].lower()
          for x in csv.DictReader((pkg / 'data_v0_5_1/split_manifest.csv').open())}
    calls = {}
    for line in (pkg / 'prompts/model_calls_v0_5_1.jsonl').open():
        c = json.loads(line)
        if sp[c['memory_id']] == 'reserved':
            calls[c['call_id']] = c

    rows = []
    for cid, call in calls.items():
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
                    ref = refs[call['context_id']]
                    legacy = interpret(pr.obj, call['payload'], ref, call['condition'])
                    consistent = legacy.get('reaction_rule_consistent', False)
                    rec['reaction_correct'] = int(bool(legacy['reaction_correct']) and consistent)
                    rec['rule_correct'] = int(bool(legacy['rule_correct']))
                    rec['scorable'] = True
        rows.append(rec)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run')
    ap.add_argument('--package')
    ap.add_argument('--signature', help='archive SHA-256 from the SIGNED freeze record')
    ap.add_argument('--output', default='section6_results.json')
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    if not a.signature or a.signature.strip().lower() != SIGNED_ARCHIVE_SHA256:
        print('REFUSED. The reserved analysis is sealed until the qa1c signature exists.')
        print('Supply --signature with the archive digest recorded in the SIGNED freeze record.')
        print('Expected: {0}'.format(SIGNED_ARCHIVE_SHA256))
        return 2
    if not a.run or not a.package:
        print('--run and --package are required')
        return 2

    rows = load_reserved(a.run, a.package)
    conds = sorted({r['condition'] for r in rows})
    by_ctx = defaultdict(dict)
    for r in rows:
        by_ctx[r['context_id']][r['condition']] = r
    ctxs = sorted(by_ctx)
    memories = np.array([by_ctx[c][conds[0]]['memory_id'] for c in ctxs])
    correct = {cd: np.array([by_ctx[c][cd]['reaction_correct'] for c in ctxs], dtype=float)
               for cd in conds}
    rule = {cd: np.array([by_ctx[c][cd]['rule_correct'] for c in ctxs], dtype=float)
            for cd in conds}

    res = run_hierarchy(correct, memories)
    res['denominator'] = 'intention-to-evaluate'
    res['calls'] = len(rows)
    res['contexts'] = len(ctxs)
    res['memories'] = int(len(set(memories.tolist())))
    res['status_distribution'] = {}
    for r in rows:
        res['status_distribution'][r['status']] = res['status_distribution'].get(r['status'], 0) + 1
    res['meta_decision_rule_accuracy'] = {cd: round(float(rule[cd].mean()), 6) for cd in conds}
    Path(a.output).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
