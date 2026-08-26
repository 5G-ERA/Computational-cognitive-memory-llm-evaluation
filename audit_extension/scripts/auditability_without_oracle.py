#!/usr/bin/env python3
"""Oracle-free error localisation by self-inconsistency, and its recall.

Companion to the section 15 join. NOT part of the audit pipeline.

The detector: each canonical context has one correct rule and is delivered in
three renderings that differ only in wording. If the three responses return
different rules, at least one is wrong. That is certified by logic alone; the
oracle is never consulted inside the detector.

The oracle enters only to SCORE the detector - to count how many erroneous
contexts it catches (recall) and to confirm that every flagged context does
contain an error (precision, 100 percent by construction). Reading the oracle
therefore requires the same signed inspection authorisation as the join.

Exploratory and post hoc: this analysis was built in answer to a question put on
22 August 2026, after the audit was frozen. It is not a pre-specified endpoint.
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

CONDS = ("B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--authorisation", required=True)
    ap.add_argument("--repeat-run", help="a second run of identical calls, for identical replay")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    auth = json.loads(Path(a.authorisation).read_text())
    if "INSPECTION" not in auth.get("authorises", "").upper():
        sys.exit(f"{a.authorisation} does not authorise inspection")

    groups = collections.defaultdict(dict)
    for line in open(Path(a.run) / "scoring_records.jsonl"):
        r = json.loads(line)
        if r.get("status") != "COMPLETED_VALID":
            continue
        groups[(r["canonical_id"], r["condition"])][r["context_id"][-3:]] = {
            "rule": r["parsed"]["rule_id"],
            "cites": frozenset(r["parsed"]["decisive_event_ids"]),
            "rule_correct": bool(r["rule_correct"]),
            "reaction_correct": bool(r["reaction_correct"]),
        }

    report = {"label": a.label, "inspection_authorisation": auth.get("record_id"),
              "analysis_status": "EXPLORATORY_POST_HOC",
              "detector": ("rule disagreement across the three renderings of one canonical "
                           "context; oracle-free; precision 100 percent by construction"),
              "by_condition": {}}

    for cond in CONDS:
        gs = [v for k, v in groups.items() if k[1] == cond and len(v) == 3]
        flagged = [v for v in gs if len({x["rule"] for x in v.values()}) > 1]
        has_err = lambda v: any(not x["rule_correct"] for x in v.values())
        all_ok = lambda v: all(x["reaction_correct"] for x in v.values())
        stable = lambda v: len({x["cites"] for x in v.values()}) == 1
        n_err = sum(1 for v in gs if has_err(v))
        caught = sum(1 for v in flagged if has_err(v))
        right, wrong = [v for v in gs if all_ok(v)], [v for v in gs if not all_ok(v)]
        report["by_condition"][cond] = {
            "contexts": len(gs),
            "flagged": len(flagged),
            "flagged_containing_error": caught,
            "precision": (100.0 * caught / len(flagged)) if flagged else None,
            "contexts_with_error": n_err,
            "recall": (100.0 * caught / n_err) if n_err else None,
            "consistently_wrong_invisible": sum(
                1 for v in gs if not has_err(v) is False and len({x["rule"] for x in v.values()}) == 1
                and all(not x["rule_correct"] for x in v.values())),
            "citation_stability_among_all_correct": (100.0 * sum(map(stable, right)) / len(right)) if right else None,
            "citation_stability_among_with_error": (100.0 * sum(map(stable, wrong)) / len(wrong)) if wrong else None,
            "n_all_correct": len(right), "n_with_error": len(wrong),
        }
    # Identical replay: the same call repeated. Renxi Qiu, 22 August 2026: audit is
    # reconstruction AND replay. Invariant replay (three renderings) tests reading of content;
    # identical replay tests stochastic stability. Both are oracle-free detectors; both are
    # scored here with the oracle.
    if a.repeat_run:
        rep = {}
        for line in open(Path(a.repeat_run) / "scoring_records.jsonl"):
            r = json.loads(line)
            if r.get("status") == "COMPLETED_VALID":
                rep[r["call_id"]] = {"rule": r["parsed"]["rule_id"],
                                     "cites": frozenset(r["parsed"]["decisive_event_ids"]),
                                     "rule_correct": bool(r["rule_correct"])}
        first = {}
        for line in open(Path(a.run) / "scoring_records.jsonl"):
            r = json.loads(line)
            if r.get("status") == "COMPLETED_VALID":
                first[r["call_id"]] = {"cond": r["condition"], "rule": r["parsed"]["rule_id"],
                                       "cites": frozenset(r["parsed"]["decisive_event_ids"]),
                                       "rule_correct": bool(r["rule_correct"])}
        report["identical_replay"] = {"repeat_run": a.repeat_run, "by_condition": {}}
        for cond in CONDS:
            ids = [c for c in first if c in rep and first[c]["cond"] == cond]
            flagged = [c for c in ids if first[c]["rule"] != rep[c]["rule"]]
            err = [c for c in ids if not first[c]["rule_correct"] or not rep[c]["rule_correct"]]
            caught = sum(1 for c in flagged if c in set(err))
            report["identical_replay"]["by_condition"][cond] = {
                "calls": len(ids),
                "same_rule": (100.0 * sum(1 for c in ids if first[c]["rule"] == rep[c]["rule"]) / len(ids)) if ids else None,
                "same_citations": (100.0 * sum(1 for c in ids if first[c]["cites"] == rep[c]["cites"]) / len(ids)) if ids else None,
                "flagged": len(flagged), "flagged_containing_error": caught,
                "precision": (100.0 * caught / len(flagged)) if flagged else None,
                "calls_with_error": len(err),
                "recall": (100.0 * caught / len(err)) if err else None}

    Path(a.out).write_text(json.dumps(report, indent=2))
    for c, v in report["by_condition"].items():
        print(f"{a.label} {c}: recall {v['recall']:.1f}% precision {v['precision']:.0f}% "
              f"invisible {v['consistently_wrong_invisible']} | cite-stability right "
              f"{v['citation_stability_among_all_correct']:.1f}% wrong {v['citation_stability_among_with_error']:.1f}%")


if __name__ == "__main__":
    main()
