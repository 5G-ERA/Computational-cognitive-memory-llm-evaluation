#!/usr/bin/env python3
"""EXP1: test the Terra-generated family hypothesis on KIMI2 and Qwen3 reserved.
Pre-registration f65709957165ef86c9bf025d17e0de4160b4dbc2d23e4b79e5ccb912b564c2d2.
Uses the signed estimator and the release's own scorer. Nothing reimplemented."""
import json, csv, sys, importlib.util, collections
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent.parent
REL = HERE.parent / 'release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c'
FROZEN = Path('/home/ros/Downloads/deliverable 2/analysis/analysis_section6.py')

spec = importlib.util.spec_from_file_location('frozen', FROZEN)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

fam = {r['context_id']: r['template_family'] for r in csv.DictReader((REL/'data_v0_5_1/contexts.csv').open())}
CONDS = ['B0_LLM_ALONE', 'M0_OPEN_LOOP_MEMORY', 'B1_VERIFIED_MEMORY']
TG = 'TEMPORAL_GAP'

def rows_qwen3():
    sc = [json.loads(l) for l in (HERE/'out/reserved_qwen3/scoring_records.jsonl').open()]
    return [dict(ctx=s['context_id'], mem=s['memory_id'], cond=s['condition'],
                 ok=int(bool(s['status'] == 'COMPLETED_VALID' and s.get('reaction_correct')
                             and s.get('reaction_rule_consistent', True)))) for s in sc]

def rows_kimi():
    run = HERE.parent/'reserved_run_2026-08-15/medical_assumption_memory_computational_benchmark_v0_5_1_qa1b/results/reserved_2026-08-15'
    rs = m.load_reserved(str(run), str(REL))       # signed loader, qa1c parser
    return [dict(ctx=r['context_id'], mem=r['memory_id'], cond=r['condition'],
                 ok=int(r['reaction_correct'])) for r in rs]

def frame(rows):
    d = collections.defaultdict(dict); mem = {}
    for r in rows:
        d[r['ctx']][r['cond']] = r['ok']; mem[r['ctx']] = r['mem']
    ctx = [c for c in d if len(d[c]) == 3]
    return (pd.DataFrame([{k: d[c][k] for k in CONDS} for c in ctx]),
            pd.Series([mem[c] for c in ctx]), [fam[c] for c in ctx])

def did_bootstrap(correct, memories, fams, n_boot=10000, seed=13082654):
    """(B1-B0 | TEMPORAL_GAP) - (B1-B0 | other four). Clustered on memory, as frozen."""
    fams = np.array(fams); tg = fams == TG
    b1 = correct['B1_VERIFIED_MEMORY'].to_numpy(); b0 = correct['B0_LLM_ALONE'].to_numpy()
    mem = memories.to_numpy()
    def stat(idx):
        t = tg[idx]
        if t.sum() == 0 or (~t).sum() == 0: return np.nan
        return (b1[idx][t].mean()-b0[idx][t].mean()) - (b1[idx][~t].mean()-b0[idx][~t].mean())
    est = stat(np.arange(len(b1)))
    clusters = np.unique(mem); byc = {c: np.where(mem == c)[0] for c in clusters}
    rng = np.random.default_rng(seed); boot = []
    for _ in range(n_boot):
        pick = rng.choice(clusters, size=len(clusters), replace=True)
        idx = np.concatenate([byc[c] for c in pick])
        s = stat(idx)
        if not np.isnan(s): boot.append(s)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return 100*est, [100*lo, 100*hi]

out = {'prereg_sha256': 'f65709957165ef86c9bf025d17e0de4160b4dbc2d23e4b79e5ccb912b564c2d2', 'models': {}}
for name, loader in (('KIMI2', rows_kimi), ('Qwen3', rows_qwen3)):
    correct, memories, fams = frame(loader())
    res = {'n_contexts': len(fams)}
    byfam = {}
    for f in sorted(set(fams)):
        sel = [i for i, x in enumerate(fams) if x == f]
        byfam[f] = {c: round(float(correct[c].iloc[sel].mean()), 6) for c in CONDS}
        byfam[f]['B1_minus_B0_pp'] = round(100*(byfam[f]['B1_VERIFIED_MEMORY']-byfam[f]['B0_LLM_ALONE']), 4)
    res['by_family'] = byfam
    b0s = {f: byfam[f]['B0_LLM_ALONE'] for f in byfam}
    res['H1_lowest_B0_family'] = min(b0s, key=b0s.get)
    res['H1_holds'] = bool(res['H1_lowest_B0_family'] == TG)
    other = [f for f in byfam if f != TG]
    res['B1_minus_B0_TEMPORAL_GAP_pp'] = byfam[TG]['B1_minus_B0_pp']
    res['B1_minus_B0_other_mean_pp'] = round(sum(byfam[f]['B1_minus_B0_pp'] for f in other)/len(other), 4)
    est, ci = did_bootstrap(correct, memories, fams)
    res['difference_in_differences_pp'] = round(est, 4)
    res['difference_in_differences_ci95'] = [round(ci[0], 4), round(ci[1], 4)]
    res['H2_holds'] = bool(est > 0)
    out['models'][name] = res

out['H1_replicates_in_both'] = all(out['models'][k]['H1_holds'] for k in out['models'])
out['H2_replicates_in_both'] = all(out['models'][k]['H2_holds'] for k in out['models'])
Path(HERE/'exp/exp1_family_pattern.json').write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
