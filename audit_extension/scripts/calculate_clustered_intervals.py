#!/usr/bin/env python3
"""Protocol section 15: paired memory-clustered bootstrap and permutation test.

The memory group is the independent unit. Every context, rendering, condition
and audit record derived from one memory stays inside that memory's cluster, so
a resample draws whole memories and keeps all of their rows together.
"""
from __future__ import annotations
import numpy as np

BOOT = 10_000
PERM = 10_000
SEED = 13082652


def _rate(rows, key="conformant"):
    """rows: list of (numerator, denominator) pairs already reduced per memory."""
    num = sum(r[0] for r in rows)
    den = sum(r[1] for r in rows)
    return (num / den) if den else float("nan")


def paired_difference(per_memory_a, per_memory_b, memories, boot=BOOT, seed=SEED):
    """Paired memory-clustered bootstrap of rate(a) - rate(b).

    per_memory_*: {memory_id: (numerator, denominator)}
    Returns dict with point estimate, 95% percentile interval and the resample
    count that was usable.
    """
    rng = np.random.default_rng(seed)
    mems = [m for m in memories if m in per_memory_a and m in per_memory_b]
    if not mems:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "clusters": 0, "resamples": 0}
    a = np.array([per_memory_a[m] for m in mems], dtype=float)   # (n, 2)
    b = np.array([per_memory_b[m] for m in mems], dtype=float)
    point = (a[:, 0].sum() / a[:, 1].sum() if a[:, 1].sum() else np.nan) - \
            (b[:, 0].sum() / b[:, 1].sum() if b[:, 1].sum() else np.nan)
    n = len(mems)
    idx = rng.integers(0, n, size=(boot, n))
    an, ad = a[:, 0][idx].sum(1), a[:, 1][idx].sum(1)
    bn, bd = b[:, 0][idx].sum(1), b[:, 1][idx].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.where((ad > 0) & (bd > 0), an / ad - bn / bd, np.nan)
    ok = d[~np.isnan(d)]
    lo, hi = (np.percentile(ok, [2.5, 97.5]) if ok.size else (np.nan, np.nan))
    return {"point": float(point) * 100, "lo": float(lo) * 100, "hi": float(hi) * 100,
            "clusters": n, "resamples": int(ok.size)}


def paired_permutation(per_memory_a, per_memory_b, memories, perm=PERM, seed=SEED):
    """Robustness analysis: flip the condition label within each memory cluster."""
    rng = np.random.default_rng(seed + 1)
    mems = [m for m in memories if m in per_memory_a and m in per_memory_b]
    if not mems:
        return {"p": float("nan"), "clusters": 0}
    a = np.array([per_memory_a[m] for m in mems], dtype=float)
    b = np.array([per_memory_b[m] for m in mems], dtype=float)
    obs = abs((a[:, 0].sum() / a[:, 1].sum()) - (b[:, 0].sum() / b[:, 1].sum()))
    n = len(mems)
    flip = rng.integers(0, 2, size=(perm, n)).astype(bool)
    an = np.where(flip, b[:, 0], a[:, 0]).sum(1)
    ad = np.where(flip, b[:, 1], a[:, 1]).sum(1)
    bn = np.where(flip, a[:, 0], b[:, 0]).sum(1)
    bd = np.where(flip, a[:, 1], b[:, 1]).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        stat = np.abs(an / ad - bn / bd)
    p = float((np.sum(stat >= obs - 1e-12) + 1) / (perm + 1))
    return {"p": p, "observed": float(obs) * 100, "clusters": n}


def holm(pvalues: dict):
    """Holm adjustment, used only if all six parent domains are tested."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        out[k] = running
    return out


if __name__ == "__main__":
    print(__doc__)
