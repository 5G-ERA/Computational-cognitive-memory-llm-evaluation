#!/usr/bin/env python3
"""Protocol section 14: existing-data reproducibility checks. No model calls.

Representation stability
  For each memory, the shared M0 prospective fields and the B1 preserved fields
  must be invariant across all five current contexts and all three renderings.
  Canonical hashes of invariant objects must match; a mismatch is a dataset,
  projection or rendering defect.

Cross-rendering response consistency
  For each canonical context and condition, compare the returned decision, rule
  and cited evidence across the three renderings. Reports exact agreement and
  Jaccard similarity of the evidence sets. This measures presentation
  stability, not repeated stochastic-call reproducibility.
"""
from __future__ import annotations
import argparse, collections, itertools, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Release, Run
from canonicalise_trace import canonicalise_response, prospective_hash, sha256_obj
from calculate_clustered_intervals import paired_difference, paired_permutation, holm


def representation_stability(rel: Release, split: str):
    pro, res = collections.defaultdict(set), collections.defaultdict(set)
    for c in rel.calls.values():
        if rel.split[c["memory_id"]] != split:
            continue
        p = c["payload"]
        if "open_loop_memory" in p:
            o = p["open_loop_memory"]
            pro[c["memory_id"]].add(prospective_hash(o.get("assumption"),
                                                     o.get("expected_consequence"),
                                                     o.get("alternative")))
        if "verified_cognitive_memory" in p:
            m = p["verified_cognitive_memory"]
            q = m.get("prospective") or {}
            pro[c["memory_id"]].add(prospective_hash(q.get("assumption"),
                                                     q.get("expected_consequence"),
                                                     q.get("alternative")))
            res[c["memory_id"]].add(sha256_obj({
                "resolved_relation": m.get("resolved_relation"),
                "comparison_guide": m.get("comparison_guide"),
                "successor_relation": m.get("successor_relation"),
            }))
    unstable_pro = sorted(m for m, h in pro.items() if len(h) > 1)
    unstable_res = sorted(m for m, h in res.items() if len(h) > 1)
    return {
        "memories": len(pro),
        "prospective_invariant": not unstable_pro,
        "resolved_invariant": not unstable_res,
        "unstable_prospective_memories": unstable_pro,
        "unstable_resolved_memories": unstable_res,
        "note": ("The prospective hash is compared across conditions as well as contexts and "
                 "renderings, so this also certifies M0/B1 prospective equality per memory."),
    }


def cross_rendering(rel: Release, run: Run, split: str):
    by = collections.defaultdict(dict)
    for c in rel.calls.values():
        if rel.split[c["memory_id"]] != split:
            continue
        r = run.parsed.get(c["call_id"])
        if r is None:
            continue
        can = canonicalise_response(r.get("parsed"))
        if not can.get("parseable"):
            continue
        rend = rel.context_map[c["context_id"]]["rendering"]
        by[(c["canonical_id"], c["condition"])][rend] = can

    per_condition = collections.defaultdict(lambda: {
        "groups": 0, "reaction_agree": 0, "rule_agree": 0, "citation_exact": 0,
        "jaccard_sum": 0.0, "pairs": 0})
    for (canon, cond), d in by.items():
        if len(d) < 2:
            continue
        s = per_condition[cond]
        s["groups"] += 1
        s["reaction_agree"] += len({v["reaction"] for v in d.values()}) == 1
        s["rule_agree"] += len({v["rule_id"] for v in d.values()}) == 1
        sets = [frozenset(v["decisive_event_ids"] or []) for v in d.values()]
        s["citation_exact"] += len(set(sets)) == 1
        for a, b in itertools.combinations(sets, 2):
            u = a | b
            s["jaccard_sum"] += (len(a & b) / len(u)) if u else 1.0
            s["pairs"] += 1

    out = {}
    for cond, s in per_condition.items():
        g = s["groups"] or 1
        out[cond] = {
            "canonical_contexts": s["groups"],
            "reaction_exact_agreement": s["reaction_agree"] / g,
            "rule_exact_agreement": s["rule_agree"] / g,
            "citation_set_exact_agreement": s["citation_exact"] / g,
            "citation_jaccard_mean": (s["jaccard_sum"] / s["pairs"]) if s["pairs"] else None,
        }
    return out


def cross_rendering_contrast(rel: Release, run: Run, split: str):
    """Memory-clustered interval on the B1 minus B0 difference in rendering stability.

    Added after FINDING_003: a headline that separates conditions must carry an interval,
    and must be computed by the pipeline rather than by an ad-hoc script. Only canonical
    contexts with all three renderings present enter, and the count of dropped groups is
    reported so a selection effect cannot hide.
    """
    groups, dropped, unparseable = {}, collections.Counter(), collections.Counter()
    for c in rel.calls.values():
        if rel.split[c["memory_id"]] != split:
            continue
        r = run.parsed.get(c["call_id"])
        can = canonicalise_response(r.get("parsed") if r else None)
        if not can.get("parseable"):
            unparseable[c["condition"]] += 1
            continue
        key = (c["memory_id"], c["canonical_id"], c["condition"])
        groups.setdefault(key, {})[rel.context_map[c["context_id"]]["rendering"]] = can

    out = {"unparseable_responses": dict(unparseable), "contrasts": {}}
    for name, keyfn in (("citation_set_exact",
                         lambda v: frozenset(v["decisive_event_ids"] or [])),
                        ("reaction_exact", lambda v: v["reaction"]),
                        ("rule_exact", lambda v: v["rule_id"])):
        per = {}
        for cond in ("B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY"):
            d = collections.defaultdict(lambda: [0, 0])
            for (mem, _canon, c), v in groups.items():
                if c != cond:
                    continue
                if len(v) < 3:
                    dropped[cond] += 1
                    continue
                d[mem][1] += 1
                d[mem][0] += 1 if len({keyfn(x) for x in v.values()}) == 1 else 0
            per[cond] = {k: tuple(x) for k, x in d.items()}
        mems = sorted(set(per["B0_LLM_ALONE"]) & set(per["B1_VERIFIED_MEMORY"]))
        diff = paired_difference(per["B1_VERIFIED_MEMORY"], per["B0_LLM_ALONE"], mems)
        perm = paired_permutation(per["B1_VERIFIED_MEMORY"], per["B0_LLM_ALONE"], mems)
        worse = sum(1 for m in mems
                    if per["B1_VERIFIED_MEMORY"][m][0] / per["B1_VERIFIED_MEMORY"][m][1]
                    < per["B0_LLM_ALONE"][m][0] / per["B0_LLM_ALONE"][m][1])
        out["contrasts"][name] = {
            "B0": _rate(per["B0_LLM_ALONE"]), "M0": _rate(per["M0_OPEN_LOOP_MEMORY"]),
            "B1": _rate(per["B1_VERIFIED_MEMORY"]),
            "B1_minus_B0": diff, "permutation": perm,
            "memories_where_B1_is_worse": worse, "memories_compared": len(mems)}
    # This contrast was not pre-specified. Protocol section 14 declares the cross-rendering
    # check descriptive; quantifying it as a condition contrast is exploratory, so the three
    # measures are Holm-adjusted within the model and the status is labelled as such.
    adj = holm({k: v["permutation"]["p"] for k, v in out["contrasts"].items()})
    for k, v in out["contrasts"].items():
        v["permutation_p_holm"] = adj[k]
        v["excludes_zero"] = not (v["B1_minus_B0"]["lo"] <= 0 <= v["B1_minus_B0"]["hi"])
    out["analysis_status"] = "EXPLORATORY"
    out["analysis_note"] = ("Protocol section 14 declares cross-rendering consistency a "
        "descriptive check. Quantifying it as a memory-clustered condition contrast is an "
        "addition, not a pre-specified endpoint, and is reported as exploratory with Holm "
        "adjustment across the three measures within each model.")
    out["incomplete_groups_dropped"] = dict(dropped)
    return out


def _rate(per):
    num = sum(v[0] for v in per.values())
    den = sum(v[1] for v in per.values())
    return (100.0 * num / den) if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="development")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rel, run = Release(Path(a.release)), Run(Path(a.run))
    report = {
        "split": a.split,
        "representation_stability": representation_stability(rel, a.split),
        "cross_rendering_response_consistency": cross_rendering(rel, run, a.split),
        "cross_rendering_contrast": cross_rendering_contrast(rel, run, a.split),
        "scope_note": ("Repeated identical-call trace reproducibility is out of scope here and "
                       "requires the separate prospectively frozen extension of protocol "
                       "section 21."),
    }
    Path(a.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
