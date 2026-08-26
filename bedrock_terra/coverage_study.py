#!/usr/bin/env python3
"""How optimistic is the frozen interval? A coverage study, run before unsealing.

FINDING_002 of the KIMI2 reserved analysis disclosed that the frozen percentile
bootstrap over 32 memory clusters undercovers. That disclosure rested on a coarse
check inside the estimator's own self-test: 400 replicates at a single scenario.
This quantifies it properly, across a grid, so the number can be stated in the
paper rather than gestured at.

Run BEFORE the reserved outcome is inspected. Nothing here touches run data; it is
pure simulation against a known truth, so no result can be tuned to it.

The estimator is imported from the signed analysis_section6.py and is NOT altered.
The point is to characterise the disclosure, never to fix it: the estimator is
frozen and stays frozen.

Design. Memory-level dependence has two parts and only one of them matters:

    u ~ N(0, 0.10)   level shared by both conditions within a memory -> CANCELS in
                     the difference, so it creates no clustered dependence in the
                     estimand
    v ~ N(0, 0.18)   memory-specific BENEFIT, the memory-by-condition interaction
                     -> does NOT cancel, and is the reason clustering is required

Simulating only u is the mistake made on 16 August 2026; it makes the clustered
and unclustered intervals look equivalent because there is nothing to cluster on.

  python3 coverage_study.py --reps 1000 --boot 2000 --out out/coverage_study.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np

FROZEN = Path('/home/ros/Downloads/deliverable 2/analysis/analysis_section6.py')
PER_MEM = 15                      # contexts per memory per condition, as in v0.5.1
U_SD, V_SD = 0.10, 0.18
A, B = 'B1_VERIFIED_MEMORY', 'B0_LLM_ALONE'


def load_frozen():
    spec = importlib.util.spec_from_file_location('frozen_section6', FROZEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def one_cell(frozen, n_mem, p0, effect, reps, boot, seed0):
    """Return coverage, one-sided false-positive / power, and mean interval width."""
    mem = np.repeat(np.arange(n_mem), PER_MEM)
    n = len(mem)
    covered = cleared = 0
    widths = []
    for rep in range(reps):
        rng = np.random.RandomState(seed0 + rep)
        u = rng.normal(0, U_SD, n_mem)[mem]
        v = rng.normal(0, V_SD, n_mem)[mem]
        pb = np.clip(p0 + u, .01, .99)
        pa = np.clip(p0 + effect + u + v, .01, .99)
        correct = {B: (rng.rand(n) < pb).astype(float),
                   A: (rng.rand(n) < pa).astype(float)}
        bs = frozen.cluster_bootstrap(correct, mem, A, B, n_boot=boot, seed=seed0 + rep)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        covered += int(lo <= effect <= hi)
        cleared += int(lo > 0)
        widths.append(hi - lo)
    return {
        'coverage': round(covered / reps, 4),
        'lower_bound_clears_zero': round(cleared / reps, 4),
        'mean_ci_width_pp': round(100 * float(np.mean(widths)), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--reps', type=int, default=1000)
    ap.add_argument('--boot', type=int, default=2000)
    ap.add_argument('--out', default='out/coverage_study.json')
    a = ap.parse_args()

    frozen = load_frozen()
    grid_mem = [(8, 'development split'), (32, 'reserved split')]
    grid_p0 = [0.33, 0.55, 0.75]
    grid_eff = [0.00, 0.10, 0.18]

    started = time.time()
    cells = []
    seed = 900000
    for n_mem, label in grid_mem:
        for p0 in grid_p0:
            for eff in grid_eff:
                r = one_cell(frozen, n_mem, p0, eff, a.reps, a.boot, seed)
                seed += a.reps
                r.update({'memories': n_mem, 'split': label, 'baseline': p0,
                          'true_effect_pp': round(100 * eff, 1)})
                cells.append(r)
                print('{0:2d} mem  base {1:.2f}  effect {2:5.1f} pp  ->  '
                      'coverage {3:6.1%}  clears zero {4:6.1%}  width {5:5.2f} pp'.format(
                          n_mem, p0, 100 * eff, r['coverage'],
                          r['lower_bound_clears_zero'], r['mean_ci_width_pp']), flush=True)

    def summarise(n_mem, effect):
        sel = [c for c in cells if c['memories'] == n_mem and c['true_effect_pp'] == effect]
        return {
            'coverage_min': min(c['coverage'] for c in sel),
            'coverage_max': max(c['coverage'] for c in sel),
            'coverage_mean': round(sum(c['coverage'] for c in sel) / len(sel), 4),
            'clears_zero_mean': round(
                sum(c['lower_bound_clears_zero'] for c in sel) / len(sel), 4),
        }

    out = {
        'purpose': ('Quantify the undercoverage disclosed as FINDING_002, before any '
                    'reserved outcome is inspected. The frozen estimator is characterised, '
                    'not altered.'),
        'estimator_source': str(FROZEN),
        'estimator_altered': False,
        'design': {'contexts_per_memory_per_condition': PER_MEM,
                   'shared_memory_sd': U_SD,
                   'memory_by_condition_interaction_sd': V_SD,
                   'note': ('The interaction is what creates clustered dependence in the '
                            'difference; a shared memory effect cancels and is not enough '
                            'to exercise the estimator.')},
        'replicates_per_cell': a.reps,
        'bootstrap_replicates': a.boot,
        'nominal_coverage': 0.95,
        'nominal_one_sided_alpha': 0.025,
        'cells': cells,
        'headline': {
            'reserved_32_memories_under_null': summarise(32, 0.0),
            'reserved_32_memories_effect_10pp': summarise(32, 10.0),
            'development_8_memories_under_null': summarise(8, 0.0),
            'development_8_memories_effect_10pp': summarise(8, 10.0),
        },
        'elapsed_seconds': round(time.time() - started, 1),
    }
    Path(a.out).write_text(json.dumps(out, indent=2))
    print('\nwritten to %s in %.0f s' % (a.out, out['elapsed_seconds']))
    print(json.dumps(out['headline'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
