#!/usr/bin/env python3
"""Protocol section 15: join audit results with decision accuracy, AFTER both are frozen.

This script is NOT part of the audit pipeline and must never be imported by it. It
reads scoring_records.jsonl on purpose: the join is the one step where the oracle is
permitted, and only under an inspection authorisation for the run. It answers a
question the oracle-free audit cannot:

    Does trace reconstructibility carry information about correctness, or is the
    stated rationale unrelated to whether the decision was right?

If the LLM's stated pathway were pure confabulation, audit status and correctness
would be independent. If the pathway is informative, non-conformant traces should be
wrong more often than conformant ones.
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calculate_clustered_intervals import paired_difference

CONDS = ("B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY")


def load_scoring(run_dir: Path):
    out = {}
    for line in open(run_dir / "scoring_records.jsonl"):
        r = json.loads(line)
        if r.get("status") == "COMPLETED_VALID" and "reaction_correct" in r:
            out[r["call_id"]] = bool(r["reaction_correct"])
    return out


def load_audit(results_dir: Path):
    status, cites = {}, {}
    for line in open(results_dir / "audit_case_summaries.jsonl"):
        s = json.loads(line)
        if s["reading"] == "SCOPED" and s["audit_level"] == "L1_IO":
            status[s["call_id"]] = (s["case_status"], s["memory_id"], s["condition"],
                                    s["canonical_id"])
    return status


def cluster_rate(pairs):
    """pairs: {memory: [numerator, denominator]} -> pooled rate or None."""
    n = sum(v[0] for v in pairs.values()); d = sum(v[1] for v in pairs.values())
    return (100.0 * n / d) if d else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--authorisation", required=True,
                    help="path of the signed inspection record covering this run")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    auth = json.loads(Path(a.authorisation).read_text())
    if "INSPECTION" not in auth.get("authorises", "").upper():
        sys.exit(f"{a.authorisation} does not authorise inspection")

    correct = load_scoring(Path(a.run))
    audit = load_audit(Path(a.results))

    report = {"label": a.label, "inspection_authorisation": auth.get("record_id"),
              "protocol_section": 15, "reading": "SCOPED", "audit_level": "L1_IO",
              "by_condition": {}}

    for cond in CONDS:
        cells = collections.Counter()
        conf_corr = collections.defaultdict(lambda: [0, 0])
        nonc_corr = collections.defaultdict(lambda: [0, 0])
        for cid, (st, mem, c, _) in audit.items():
            if c != cond or cid not in correct:
                continue
            ok = correct[cid]; conformant = st == "CONFORMANT"
            cells[("correct" if ok else "incorrect",
                   "conformant" if conformant else "nonconformant")] += 1
            tgt = conf_corr if conformant else nonc_corr
            tgt[mem][1] += 1; tgt[mem][0] += int(ok)
        mems = sorted(set(conf_corr) | set(nonc_corr))
        n_nonc = sum(v[1] for v in nonc_corr.values())
        diff = (paired_difference(
                    {m: tuple(conf_corr[m]) for m in mems if conf_corr[m][1]},
                    {m: tuple(nonc_corr[m]) for m in mems if nonc_corr[m][1]},
                    [m for m in mems if conf_corr[m][1] and nonc_corr[m][1]])
                if n_nonc else None)
        report["by_condition"][cond] = {
            "cells": {f"{k[0]}_{k[1]}": v for k, v in sorted(cells.items())},
            "accuracy_given_conformant": cluster_rate(conf_corr),
            "accuracy_given_nonconformant": cluster_rate(nonc_corr),
            "n_nonconformant": n_nonc,
            "difference_conformant_minus_nonconformant": diff,
            "note": ("The nonconformant cell is small by construction; the difference is "
                     "descriptive and its interval is computed only over memories with "
                     "both kinds of case."),
        }
    Path(a.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
