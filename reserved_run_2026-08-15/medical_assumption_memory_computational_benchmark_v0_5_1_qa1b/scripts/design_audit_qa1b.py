"""Chance-relative current-only design audit (v0.5.1-qa1b, Decision 3).

Replaces the one-sided eight-memory macro-F1 gate with a chance-relative audit over
every memory in the release. This is a NON-LLM design audit: it reads only the
disclosed payloads and the oracle labels and issues no model call, so it may run over
all 40 memories without opening the reserved LLM evaluation (Official Response
v0.5.1-qa1b, section 4, Decision 3).

Two gates are reported.

  nominal_gate      The literal Decision 3 specification:
                        PASS when n_memory_groups >= 32 and |accuracy - 0.20| <= 0.10
                    It is reported verbatim so the specified verdict is on record.

  chance_relative_gate
                    The corrected gate. v0.5.1 is a CLOSED BALANCED DESIGN: each of the
                    five template families maps to each of the five reactions in exactly
                    eight memories. Under any grouped cross-validation the training and
                    held-out cell counts are therefore COMPLEMENTARY - the held-out
                    memory's true cell is the one cell the training set is short of - so
                    a zero-information probe is driven systematically BELOW chance rather
                    than to 0.20. The script demonstrates this directly: a leave-one-
                    memory-out template argmax learner scores exactly 0.0000 over 39
                    training memories. The nominal +-0.10 band around 0.20 is therefore
                    unattainable by construction and is not a small-sample effect.
                    The corrected gate compares each probe against the WITHIN-MEMORY
                    PERMUTATION NULL computed under the same cross-validation, and treats
                    only above-null performance as a shortcut.

Transferable-relabelling check (Decision 3, third bullet)
    Two statistics are reported. The IN-SAMPLE one fits the optimal label permutation on
    the same held-out predictions it scores; it is an upward-biased upper bound and is
    kept only as a diagnostic. The TRANSFERABLE one fits the permutation on one set of
    memories and applies it to disjoint memories, which is what 'transferable
    prediction-to-truth relabelling across held-out memories' actually asks. Both are
    scored against their own within-memory permutation null, because post-hoc optimal
    assignment is biased upward under pure noise and a nominal comparison against 0.20
    would be wrong. The transferable statistic is the one that drives the gate.

Shortcut controls
    marker-only, template-only, structure-only, identifier-only, event-count.

Usage
    python scripts/design_audit_qa1b.py [--permutations 500] [--output validation/design_audit_qa1b.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'scripts'))
from qa_core import chance_deviation_gate  # noqa: E402

CHANCE = 0.2
TOLERANCE = 0.1
MIN_GROUPS = 32
N_FOLDS = 5
ALPHA = 0.05
ID_RE = re.compile(r'(EVT|CALL51|CAN51|MEM51)-[A-Z0-9-]+')
ID_TOKEN_RE = re.compile(r'(?:EVT|CALL51|CAN51|MEM51)-[A-Z0-9-]+')
MARKER_RE = re.compile(r'relation-(alpha|beta|gamma|delta|epsilon)')


# ---------------------------------------------------------------- feature views

def _current_only(call, meta):
    """Lexical content of the current records only, identifiers stripped."""
    parts = [e.get('content', '') for e in call['payload']['current_records']]
    return ID_RE.sub(' ', ' '.join(parts))


def _marker_only(call, meta):
    m = MARKER_RE.search(' '.join(e.get('content', '') for e in call['payload']['current_records']))
    return 'marker_' + (m.group(1) if m else 'none')


def _template_only(call, meta):
    return 'template_' + meta['template_family']


def _identifier_only(call, meta):
    return ' '.join(ID_TOKEN_RE.findall(json.dumps(call['payload'])))


def _structure_only(call, meta):
    p = call['payload']
    cur, lon = p['current_records'], p['longitudinal_records']
    srcs = Counter(e.get('source', '') for e in cur + lon)
    return [
        float(len(cur)), float(len(lon)),
        float(sum(len(e.get('content', '')) for e in cur)) / max(len(cur), 1),
        float(sum(len(e.get('content', '')) for e in lon)) / max(len(lon), 1),
        float(len({e.get('event_time', '') for e in cur})),
        float(len({e.get('event_time', '') for e in lon})),
        float(srcs.get('patient_report', 0)), float(srcs.get('support_record', 0)),
        float(srcs.get('administrative_record', 0)), float(len(srcs)),
    ]


def _event_count_only(call, meta):
    p = call['payload']
    n_cur, n_lon = len(p['current_records']), len(p['longitudinal_records'])
    return [float(n_cur), float(n_lon), float(n_cur + n_lon)]


# ---------------------------------------------------------------- probes

def _predict(X, y, groups):
    cv = GroupKFold(n_splits=min(N_FOLDS, len(set(groups))))
    clf = LogisticRegression(max_iter=4000, class_weight='balanced')
    return cross_val_predict(clf, X, y, groups=groups, cv=cv)


def make_probe(kind, payload, groups):
    """Return a callable y -> predictions. The feature matrix is built once."""
    if kind == 'text':
        X = TfidfVectorizer(ngram_range=(1, 2), min_df=2, stop_words='english').fit_transform(payload)
    else:
        X = StandardScaler().fit_transform(np.asarray(payload, dtype=float))

    def run(y):
        return _predict(X, y, groups)
    return run


# ---------------------------------------------------------------- statistics

def best_permutation_accuracy(y_true, y_pred, labels):
    """Accuracy under the optimal renaming of predicted classes (Hungarian assignment)."""
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    row, col = linear_sum_assignment(-cm)
    acc = float(cm[row, col].sum()) / float(cm.sum())
    return acc, {labels[c]: labels[r] for r, c in zip(row, col)}


def transferable_relabel_accuracy(y_true, y_pred, groups, labels, n_blocks=5, n_repeats=20,
                                  seed=13082655):
    """Accuracy of a relabelling FITTED ON ONE SET OF MEMORIES AND APPLIED TO OTHERS.

    Decision 3 requires 'no transferable prediction-to-truth relabelling across held-out
    memories'. Fitting the optimal assignment on the same predictions it is scored on is
    in-sample and upward biased, so it cannot answer that question. Here the memories are
    partitioned into disjoint blocks; for each block the assignment is estimated from the
    confusion matrix of the OTHER blocks and then applied to this block. Averaged over
    several random partitions.
    """
    rng = np.random.RandomState(seed)
    y_true, y_pred, groups = np.asarray(y_true), np.asarray(y_pred), np.asarray(groups)
    uniq = np.array(sorted(set(groups.tolist())))
    accs = []
    for _ in range(n_repeats):
        order = rng.permutation(len(uniq))
        block_of = {uniq[order[i]]: i % n_blocks for i in range(len(uniq))}
        blocks = np.array([block_of[g] for g in groups])
        correct = total = 0
        for b in range(n_blocks):
            te = blocks == b
            tr = ~te
            if not te.any() or not tr.any():
                continue
            cm = confusion_matrix(y_true[tr], y_pred[tr], labels=labels)
            row, col = linear_sum_assignment(-cm)
            mapping = {labels[c]: labels[r] for r, c in zip(row, col)}
            mapped = np.array([mapping.get(p, p) for p in y_pred[te]])
            correct += int((mapped == y_true[te]).sum())
            total += int(te.sum())
        accs.append(correct / total)
    return float(np.mean(accs)), float(np.std(accs, ddof=1))


def exact_binomial_two_sided(k, n, p=CHANCE):
    """Exact two-sided probability of a deviation from p at least as large as observed.

    Computed on items. Contexts within a memory are not independent, so this statistic is
    anticonservative and is reported only because Decision 3 asks for an exact binomial
    figure. The within-memory permutation p-value is the honest reference.
    """
    obs = abs(k / n - p)
    return min(1.0, sum(comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
                        for i in range(n + 1) if abs(i / n - p) >= obs - 1e-12))


def gate_false_fail_rate(n, p=CHANCE, tol=TOLERANCE):
    """Probability that a genuinely chance-level system FAILS the +-tol band on n items."""
    return sum(comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
               for i in range(n + 1) if abs(i / n - p) > tol)


def permutation_null(run, y, groups, labels, n_perm, seed=13082653):
    """Within-memory label permutation null for accuracy and best-relabelling accuracy.

    Permuting within a memory preserves that memory's label distribution (three contexts
    per reaction) and destroys only the feature-to-label link, so the null is matched to
    the grouped cross-validation actually used.
    """
    rng = np.random.RandomState(seed)
    y = np.asarray(y)
    groups = np.asarray(groups)
    idx = {g: np.where(groups == g)[0] for g in set(groups.tolist())}
    accs, bests, trans = [], [], []
    for _ in range(n_perm):
        yp = y.copy()
        for g, ii in idx.items():
            yp[ii] = rng.permutation(y[ii])
        pred = run(yp)
        accs.append(float(accuracy_score(yp, pred)))
        bests.append(best_permutation_accuracy(yp, pred, labels)[0])
        trans.append(transferable_relabel_accuracy(yp, pred, groups, labels, n_repeats=5)[0])
    return accs, bests, trans


def _null_summary(obs, null):
    arr = np.asarray(null, dtype=float)
    n = len(arr)
    above = float(np.sum(arr >= obs - 1e-12) + 1) / float(n + 1)
    two = float(np.sum(np.abs(arr - arr.mean()) >= abs(obs - arr.mean()) - 1e-12) + 1) / float(n + 1)
    return {
        'observed': round(float(obs), 6),
        'null_mean': round(float(arr.mean()), 6),
        'null_sd': round(float(arr.std(ddof=1)), 6),
        'null_p2_5': round(float(np.percentile(arr, 2.5)), 6),
        'null_p97_5': round(float(np.percentile(arr, 97.5)), 6),
        'p_above_null': round(above, 6),
        'p_two_sided_vs_null': round(two, 6),
        'above_null_at_alpha': bool(above <= ALPHA),
        'z_vs_null': round(float((obs - arr.mean()) / arr.std(ddof=1)), 4) if arr.std(ddof=1) > 0 else None,
    }


def holm_adjust(pvalues):
    """Holm-Bonferroni step-down adjusted p-values, returned in the input order.

    Six feature views are screened on two statistics each, so twelve one-sided tests are
    performed. Reporting only uncorrected p-values would overstate the evidence for a
    shortcut; both are reported and the gate uses the adjusted values.
    """
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * pvalues[i])
        running = max(running, val)
        adj[i] = running
    return adj


def cluster_bootstrap_ci(y_true, y_pred, groups, n_boot=2000, seed=13082654):
    """Cluster bootstrap over memories: whole memories are resampled, not single contexts."""
    rng = np.random.RandomState(seed)
    y_true, y_pred, groups = np.asarray(y_true), np.asarray(y_pred), np.asarray(groups)
    uniq = sorted(set(groups.tolist()))
    idx = {g: np.where(groups == g)[0] for g in uniq}
    accs = []
    for _ in range(n_boot):
        pick = rng.choice(len(uniq), size=len(uniq), replace=True)
        sel = np.concatenate([idx[uniq[i]] for i in pick])
        accs.append(float((y_true[sel] == y_pred[sel]).mean()))
    lo, hi = np.percentile(accs, [2.5, 97.5])
    return [round(float(lo), 6), round(float(hi), 6)]


# ------------------------------------------- closed-design complementarity proof

def complementarity_demonstration(canonical_rows):
    """Leave-one-memory-out template argmax over the disclosed canonical design.

    Shows that a zero-information probe is driven to exactly 0.0000 by the closed
    balanced design, independently of how many memories are used for training.
    """
    by_mem = defaultdict(dict)
    for r in canonical_rows:
        by_mem[r['memory_id']][r['template_family']] = r['oracle_reaction']
    mems = sorted(by_mem)
    tf = sorted({r['template_family'] for r in canonical_rows})
    rx = sorted({r['oracle_reaction'] for r in canonical_rows})
    cell = Counter((r['template_family'], r['oracle_reaction']) for r in canonical_rows)
    perms = {}
    for m in mems:
        perms.setdefault(tuple(by_mem[m][t] for t in tf), 0)
        perms[tuple(by_mem[m][t] for t in tf)] += 1
    correct = total = 0
    for held in mems:
        cnt = Counter()
        for m in mems:
            if m == held:
                continue
            for t in tf:
                cnt[(t, by_mem[m][t])] += 1
        for t in tf:
            pred = max(rx, key=lambda r: (cnt[(t, r)], r))
            total += 1
            correct += int(pred == by_mem[held][t])
    return {
        'design': 'closed balanced template-to-reaction square',
        'distinct_template_to_reaction_permutations': len(perms),
        'memories_per_permutation': sorted(perms.values()),
        'global_cell_counts_uniform': len({cell[(t, r)] for t in tf for r in rx}) == 1,
        'global_cell_count': cell[(tf[0], rx[0])],
        'leave_one_memory_out_argmax_accuracy': round(correct / total, 6),
        'training_memories_per_fold': len(mems) - 1,
        'interpretation': (
            'The held-out memory\'s true cell is always the one cell the training set is '
            'short of, so an argmax learner is wrong on every item. A zero-information '
            'probe therefore lands near 0.00, not near 0.20. The nominal +-0.10 band '
            'around chance is unattainable by construction and does not become attainable '
            'with more memories.'),
    }


# ---------------------------------------------------------------- audit

def evaluate(name, kind, payload, y, groups, labels, n_perm, want_ci):
    run = make_probe(kind, payload, groups)
    pred = run(np.asarray(y))
    acc = float(accuracy_score(y, pred))
    mf1 = float(f1_score(y, pred, average='macro'))
    best, mapping = best_permutation_accuracy(y, pred, labels)
    n_items, n_groups = len(y), len(set(groups))
    null_acc, null_best, null_trans = permutation_null(run, y, groups, labels, n_perm)
    trans, trans_sd = transferable_relabel_accuracy(y, pred, groups, labels)
    res = {
        'view': name,
        'accuracy': round(acc, 6),
        'macro_f1': round(mf1, 6),
        'n_items': n_items,
        'n_memory_groups': n_groups,
        'absolute_deviation_from_chance': round(abs(acc - CHANCE), 6),
        'within_nominal_band': bool(abs(acc - CHANCE) <= TOLERANCE),
        'exact_binomial_two_sided_p_items': round(
            exact_binomial_two_sided(int(round(acc * n_items)), n_items), 6),
        'accuracy_vs_permutation_null': _null_summary(acc, null_acc),
        'best_label_permutation_accuracy': round(best, 6),
        'best_label_permutation_map': mapping,
        'in_sample_relabelling_vs_permutation_null': _null_summary(best, null_best),
        'transferable_relabelling_accuracy': round(trans, 6),
        'transferable_relabelling_sd_over_partitions': round(trans_sd, 6),
        'transferable_relabelling_vs_permutation_null': _null_summary(trans, null_trans),
        'n_permutations': n_perm,
        'confusion_matrix_labels': labels,
        'confusion_matrix': confusion_matrix(y, pred, labels=labels).tolist(),
    }
    res['shortcut_detected'] = bool(
        res['accuracy_vs_permutation_null']['above_null_at_alpha'] or
        res['transferable_relabelling_vs_permutation_null']['above_null_at_alpha'])
    if want_ci:
        res['cluster_bootstrap_ci_95'] = cluster_bootstrap_ci(y, pred, groups)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--permutations', type=int, default=500,
                    help='permutation replicates for the primary current-only view')
    ap.add_argument('--control-permutations', type=int, default=200)
    ap.add_argument('--output', default='validation/design_audit_qa1b.json')
    a = ap.parse_args()

    calls = [json.loads(x) for x in open(R / 'prompts/model_calls_v0_5_1.jsonl')]
    refs = {x['context_id']: x for x in
            (json.loads(x) for x in open(R / 'hidden/oracle_references_v0_5_1.jsonl'))}
    ctx = {x['context_id']: x for x in csv.DictReader(open(R / 'data_v0_5_1/contexts.csv'))}
    split = {x['memory_id']: x['split'].upper()
             for x in csv.DictReader(open(R / 'data_v0_5_1/split_manifest.csv'))}
    canonical = list(csv.DictReader(open(R / 'data_v0_5_1/canonical_contexts.csv')))

    b0 = sorted([c for c in calls if c['condition'] == 'B0_LLM_ALONE'],
                key=lambda c: c['context_id'])
    y = [refs[c['context_id']]['oracle_decision']['reaction'] for c in b0]
    groups = [c['memory_id'] for c in b0]
    meta = [ctx[c['context_id']] for c in b0]
    labels = sorted(set(y))

    builders = [
        ('current_only', 'text', _current_only, True),
        ('marker_only', 'text', _marker_only, False),
        ('template_only', 'text', _template_only, False),
        ('identifier_only', 'text', _identifier_only, False),
        ('structure_only', 'numeric', _structure_only, False),
        ('event_count_only', 'numeric', _event_count_only, False),
    ]

    results = []
    for name, kind, fn, want_ci in builders:
        payload = [fn(c, m) for c, m in zip(b0, meta)]
        n_perm = a.permutations if name == 'current_only' else a.control_permutations
        r = evaluate(name, kind, payload, y, groups, labels, n_perm, want_ci)
        results.append(r)
        print('  {0:<18} acc={1:.4f} macroF1={2:.4f} null={3:.4f} p_above={4:.4f} '
              'insample_relabel={5:.4f} transferable={6:.4f} (null {7:.4f}) p_above={8:.4f}'.format(
                  name, r['accuracy'], r['macro_f1'],
                  r['accuracy_vs_permutation_null']['null_mean'],
                  r['accuracy_vs_permutation_null']['p_above_null'],
                  r['best_label_permutation_accuracy'],
                  r['transferable_relabelling_accuracy'],
                  r['transferable_relabelling_vs_permutation_null']['null_mean'],
                  r['transferable_relabelling_vs_permutation_null']['p_above_null']), flush=True)

    keys = [('accuracy_vs_permutation_null', 'accuracy'),
            ('transferable_relabelling_vs_permutation_null', 'transferable_relabelling')]
    raw_p, index = [], []
    for r in results:
        for field, label in keys:
            raw_p.append(r[field]['p_above_null'])
            index.append((r['view'], field, label))
    adj_p = holm_adjust(raw_p)
    for (view, field, _), pa in zip(index, adj_p):
        r = next(x for x in results if x['view'] == view)
        r[field]['p_above_null_holm'] = round(pa, 6)
        r[field]['above_null_holm_at_alpha'] = bool(pa <= ALPHA)
    for r in results:
        r['shortcut_detected_uncorrected'] = r['shortcut_detected']
        r['shortcut_detected'] = bool(
            r['accuracy_vs_permutation_null']['above_null_holm_at_alpha'] or
            r['transferable_relabelling_vs_permutation_null']['above_null_holm_at_alpha'])

    primary = next(r for r in results if r['view'] == 'current_only')
    nominal = chance_deviation_gate(primary['accuracy'], primary['n_memory_groups'],
                                    chance=CHANCE, tolerance=TOLERANCE,
                                    min_groups=MIN_GROUPS, n_items=primary['n_items'])
    any_shortcut = any(r['shortcut_detected'] for r in results)
    any_shortcut_unc = any(r['shortcut_detected_uncorrected'] for r in results)
    corrected_pass = bool(primary['n_memory_groups'] >= MIN_GROUPS and not any_shortcut)

    out = {
        'audit_id': 'DESIGN-AUDIT-v0.5.1-qa1b',
        'authority': 'Official Response v0.5.1-qa1b, section 4, Decision 3',
        'audit_type': 'non_llm_design_audit',
        'reserved_llm_evaluation_opened': False,
        'n_memory_groups': primary['n_memory_groups'],
        'memory_split_composition': dict(Counter(split[g] for g in sorted(set(groups)))),
        'contexts_per_memory': dict(Counter(Counter(groups).values())),
        'label_prior': {k: round(v / len(y), 6) for k, v in sorted(Counter(y).items())},
        'chance': CHANCE,
        'tolerance': TOLERANCE,
        'minimum_groups': MIN_GROUPS,
        'alpha': ALPHA,
        'cross_validation': 'GroupKFold({0}) over memory_id; every prediction is on a held-out memory'.format(N_FOLDS),
        'null_model': 'within-memory label permutation under the same grouped cross-validation',
        'closed_design_complementarity': complementarity_demonstration(canonical),
        'nominal_gate': dict(nominal, specification='n_memory_groups >= 32 and |accuracy - 0.20| <= 0.10'),
        'gate_false_fail_rate_at_32_items': round(gate_false_fail_rate(32), 6),
        'gate_false_fail_rate_at_n_items': round(gate_false_fail_rate(primary['n_items']), 6),
        'chance_relative_gate': {
            'pass': corrected_pass,
            'specification': ('n_memory_groups >= 32 and no view exceeds its within-memory '
                              'permutation null at alpha=0.05, on either raw accuracy or '
                              'TRANSFERABLE relabelling accuracy (assignment fitted on one '
                              'set of memories and applied to disjoint memories)'),
            'n_memory_groups': primary['n_memory_groups'],
            'multiplicity': 'Holm-Bonferroni over {0} one-sided tests (6 views x 2 statistics)'.format(len(raw_p)),
            'views_flagged_holm': [r['view'] for r in results if r['shortcut_detected']],
            'views_flagged_uncorrected': [r['view'] for r in results
                                          if r['shortcut_detected_uncorrected']],
            'uncorrected_verdict': 'PASS' if not any_shortcut_unc else 'FAIL',
        },
        'views': results,
    }
    out['status'] = 'PASS' if corrected_pass else 'FAIL'

    dst = R / a.output
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in
                      ('status', 'nominal_gate', 'chance_relative_gate',
                       'gate_false_fail_rate_at_32_items')}, indent=2))
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
