#!/usr/bin/env python3
"""Invariant-replay recall: the B1-B0 and B1-M0 contrasts for the three arms, side by side.

EXPLORATORY for everything except the KIMI2 B1-B0 contrast. That one is the
pre-registered confirmatory test and is only RE-DERIVED here from the sealed
scoring input (it must reproduce CONFIRMATORY_RESULT.json). The B1-M0 contrast
was not pre-registered for any arm: it was added on 23 November 2026 so that the
replay table reports the same two contrasts as the response-accuracy table.

Same detector, same loader, same grouping and the same interval and permutation
code as run_confirmatory_replay.py (imported, not copied). No model calls, no
oracle beyond the rule_correct field already stored in the scoring records.

How a contrast is estimated (this is why it need not equal the difference of the
two displayed percentages): the displayed recall of a condition pools every
erroneous context of that condition. The contrast is PAIRED by memory group: it
uses only the memory groups that have at least one erroneous context under BOTH
conditions, pools within those groups, and takes the difference. The interval
is the memory-clustered percentile bootstrap over the same groups.

    python3 audit_extension/scripts/replay_recall_contrasts.py
    python3 audit_extension/scripts/replay_recall_contrasts.py --check   # exit 1 if the stored file differs
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calculate_clustered_intervals import paired_difference, paired_permutation
from run_confirmatory_replay import CONDS, groups, load, sha

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parent
ARMS = {
    "KIMI2": PKG / "results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl",
    "Qwen3": ROOT / "bedrock_terra/out/reserved_qwen3/scoring_records.jsonl",
    "GPT-5.6 Terra": ROOT / "bedrock_terra/out/reserved_terra/scoring_records.jsonl",
}
OUT = PKG / "results/join/replay_recall_contrasts.json"
B0, M0, B1 = CONDS
MIN_CLUSTERS = 10   # below this a paired contrast is reported as not estimated


def per_memory_recall(rec, cond):
    full, _ = groups(rec, cond)
    R = collections.defaultdict(lambda: [0, 0])
    for (mem, _), v in full.items():
        if any(not x["ok"] for x in v.values()):
            R[mem][1] += 1
            R[mem][0] += int(len({x["rule"] for x in v.values()}) > 1)
    return {m: tuple(x) for m, x in R.items()}


def contrast(pm, a, b, mems):
    common = [m for m in mems if m in pm[a] and m in pm[b]]
    if len(common) < MIN_CLUSTERS:
        return {"estimated": False, "clusters": len(common),
                "reason": "fewer than %d memory groups with an erroneous context under both conditions" % MIN_CLUSTERS}
    d = paired_difference(pm[a], pm[b], common)
    p = paired_permutation(pm[a], pm[b], common)
    return {"estimated": True, "point": d["point"], "lo": d["lo"], "hi": d["hi"], "clusters": d["clusters"],
            "resamples": d["resamples"], "permutation_p": p["p"]}


def compute():
    res = {"endpoint": "invariant-replay recall, reserved split",
           "status": {"KIMI2 B1-B0": "pre-registered confirmatory; re-derived here, sealed result in results/kimi_confirmatory/CONFIRMATORY_RESULT.json",
                      "everything else": "exploratory, post hoc; B1-M0 added 2026-11-23 and not pre-registered for any arm"},
           "min_clusters_for_a_paired_contrast": MIN_CLUSTERS, "arms": {}}
    for arm, path in ARMS.items():
        rec = load(path)
        mems = sorted({v["mem"] for v in rec.values()})
        pm = {c: per_memory_recall(rec, c) for c in CONDS}
        cond = {}
        for c in CONDS:
            hit, n = sum(v[0] for v in pm[c].values()), sum(v[1] for v in pm[c].values())
            cond[c] = {"erroneous_contexts": n, "made_visible": hit, "recall_pct": (100.0 * hit / n) if n else None}
        res["arms"][arm] = {"input": str(path.relative_to(ROOT)), "input_sha256": sha(path), "by_condition": cond,
                            "B1_minus_B0": contrast(pm, B1, B0, mems), "B1_minus_M0": contrast(pm, B1, M0, mems)}
    return res


def show(res):
    for arm, r in res["arms"].items():
        c = r["by_condition"]
        print("%-14s B0 %5.1f%% (%d/%d)  M0 %5.1f%% (%d/%d)  B1 %5.1f%% (%d/%d)" % (
            arm, c[B0]["recall_pct"], c[B0]["made_visible"], c[B0]["erroneous_contexts"],
            c[M0]["recall_pct"], c[M0]["made_visible"], c[M0]["erroneous_contexts"],
            c[B1]["recall_pct"], c[B1]["made_visible"], c[B1]["erroneous_contexts"]))
        for k in ("B1_minus_B0", "B1_minus_M0"):
            x = r[k]
            if x["estimated"]:
                print("   %-12s %+6.2f pp [%+.2f, %+.2f]  permutation p = %.4f  clusters = %d" % (
                    k, x["point"], x["lo"], x["hi"], x["permutation_p"], x["clusters"]))
            else:
                print("   %-12s not estimated: %s (%d)" % (k, x["reason"], x["clusters"]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    res = compute()
    show(res)
    sealed = json.loads((PKG / "results/kimi_confirmatory/CONFIRMATORY_RESULT.json").read_text())["PRIMARY_recall_B1_minus_B0"]["difference"]
    k = res["arms"]["KIMI2"]["B1_minus_B0"]
    same = all(abs(k[f] - sealed[f]) < 1e-9 for f in ("point", "lo", "hi")) and k["clusters"] == sealed["clusters"]
    print("KIMI2 B1-B0 reproduces the sealed confirmatory result:", "yes" if same else "NO")
    if not same:
        sys.exit(1)
    text = json.dumps(res, indent=2) + "\n"
    if a.check:
        ok = OUT.exists() and OUT.read_text() == text
        print("stored file matches:", "yes" if ok else "NO")
        sys.exit(0 if ok else 1)
    OUT.write_text(text)
    print("written:", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
