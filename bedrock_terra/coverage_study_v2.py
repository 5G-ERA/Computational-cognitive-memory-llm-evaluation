#!/usr/bin/env python3
"""Coverage of the frozen estimator, measured against the REALISED estimand.

Supersedes coverage_study.py of the same date. That version compared each interval
against the NOMINAL effect. At high baselines the clip at p=0.99 means the nominal
effect is never realised (base 0.75, nominal 18 pp -> realised 12.5 pp), so its
high-baseline cells measured coverage of a target the simulation never generated
and collapsed for that reason alone. Corrected here: for every replicate the truth
is the realised probability-level difference, mean(pa) - mean(pb).

Estimator imported from the signed analysis_section6.py, unaltered.
"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np

F = Path('/home/ros/Downloads/deliverable 2/analysis/analysis_section6.py')
spec = importlib.util.spec_from_file_location('f', F); frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)
A, B = 'B1_VERIFIED_MEMORY', 'B0_LLM_ALONE'
PER_MEM, U_SD, V_SD = 15, 0.10, 0.18

def cell(n_mem, p0, eff, reps=1000, boot=2000, seed0=7000):
    mem = np.repeat(np.arange(n_mem), PER_MEM); n = len(mem)
    cov = clr = 0; widths = []; truths = []
    for r in range(reps):
        rng = np.random.RandomState(seed0 + r)
        u = rng.normal(0, U_SD, n_mem)[mem]; v = rng.normal(0, V_SD, n_mem)[mem]
        pb = np.clip(p0 + u, .01, .99); pa = np.clip(p0 + eff + u + v, .01, .99)
        truth = pa.mean() - pb.mean()                      # realised estimand
        c = {B: (rng.rand(n) < pb).astype(float), A: (rng.rand(n) < pa).astype(float)}
        bs = frozen.cluster_bootstrap(c, mem, A, B, n_boot=boot, seed=seed0 + r)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        cov += int(lo <= truth <= hi); clr += int(lo > 0)
        widths.append(hi - lo); truths.append(truth)
    return {'memories': n_mem, 'baseline': p0, 'nominal_effect_pp': round(100*eff, 1),
            'realised_effect_pp': round(100*float(np.mean(truths)), 2),
            'coverage': round(cov/reps, 4), 'clears_zero': round(clr/reps, 4),
            'mean_width_pp': round(100*float(np.mean(widths)), 2)}

out = {'supersedes': 'coverage_study.json (compared against the nominal, not realised, effect)',
       'truth_definition': 'realised probability-level difference per replicate',
       'estimator_altered': False, 'replicates_per_cell': 1000, 'bootstrap_replicates': 2000,
       'cells': []}
print(f"{'mem':>4} {'base':>5} {'nom':>6} {'real':>7} {'cover':>7} {'clears0':>8} {'width':>7}")
for n_mem in (8, 32):
    for p0 in (0.33, 0.55, 0.75):
        for eff in (0.0, 0.10, 0.18):
            c = cell(n_mem, p0, eff); out['cells'].append(c)
            print(f"{n_mem:4d} {p0:5.2f} {c['nominal_effect_pp']:6.1f} {c['realised_effect_pp']:7.2f} "
                  f"{c['coverage']:7.3f} {c['clears_zero']:8.3f} {c['mean_width_pp']:7.2f}", flush=True)
Path('out/coverage_study_v2.json').write_text(json.dumps(out, indent=2))
print('\nescrito out/coverage_study_v2.json')
