#!/usr/bin/env python3
"""Protocol sections 10-13 and 15: case summaries, metrics and contrasts.

Reads the three error files written by the audit scripts plus the manifest,
then writes every machine-readable output protocol section 12 requires.
Everything is computed twice, once per reading (LITERAL and SCOPED); the
`reading` column carries which is which.
"""
from __future__ import annotations
import argparse, collections, csv, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Ontology, case_status, filter_reading, read_json, PKG
from assign_root_causes import assign
from calculate_clustered_intervals import paired_difference, paired_permutation

# Decision A5, Renxi Qiu, 22 August 2026: SCOPED is normative, LITERAL is a declared
# sensitivity. SCOPED is listed first so it leads every ordered output.
READINGS = ("SCOPED", "LITERAL")
NORMATIVE_READING = "SCOPED"
LEVEL_OF_CONDITION = {
    "B0_LLM_ALONE": [("L1_IO", True)],
    "M0_OPEN_LOOP_MEMORY": [("L1_IO", True), ("L2_M0", True)],
    "B1_VERIFIED_MEMORY": [("L1_IO", True), ("L2_B1", True)],
}


def build(work: Path, ont: Ontology):
    rows = [json.loads(l) for l in open(work / "audit_manifest.jsonl")]
    errors = []
    for name in ("level1_errors.jsonl", "level2_m0_errors.jsonl", "level2_b1_errors.jsonl"):
        p = work / name
        if p.exists():
            errors += [json.loads(l) for l in open(p)]

    structural_b1 = {}
    sp = work / "level2_b1_structural.json"
    if sp.exists():
        structural_b1 = json.loads(sp.read_text())

    by_case = collections.defaultdict(list)
    for e in errors:
        by_case[(e["call_id"], e["audit_level"])].append(e)

    summaries = []
    for row in rows:
        levels = [lvl for lvl, _ in LEVEL_OF_CONDITION[row["condition"]]]
        # B0 Level 2 is a structural status, never an error and never a failure.
        if row["condition"] == "B0_LLM_ALONE":
            for reading in READINGS:
                summaries.append({**{k: row[k] for k in ("call_id", "memory_id", "context_id",
                                                         "canonical_id", "condition", "rendering")},
                                  "audit_level": "L2_B0", "case_status": "NOT_APPLICABLE",
                                  "structural_status": "NOT_APPLICABLE_BY_CONDITION_DESIGN",
                                  "evaluable": False, "reconstructible": False, "critical": False,
                                  "trace_completeness": None, "codes": [], "root_cause_id": None,
                                  "primary_error_code": None, "secondary_error_codes": [],
                                  "human_review_required": False, "reading": reading})
        for lvl in levels:
            raw = by_case.get((row["call_id"], lvl), [])
            for reading in READINGS:
                sel = filter_reading(raw, reading, ont)
                st = case_status(sel)
                rid, primary, secondary = assign(sel, ont)
                summaries.append({
                    **{k: row[k] for k in ("call_id", "memory_id", "context_id",
                                           "canonical_id", "condition", "rendering")},
                    "audit_level": lvl,
                    "case_status": st,
                    "structural_status": (
                        "OPEN_LOOP_BY_CONDITION_DESIGN" if lvl == "L2_M0"
                        else structural_b1.get(row["call_id"], {}).get("structural_status")
                        if lvl == "L2_B1" else None),
                    "evaluable": st != "NOT_EVALUABLE",
                    "reconstructible": st in ("CONFORMANT", "INCOMPLETE", "NONCONFORMANT"),
                    "critical": st == "NONCONFORMANT_CRITICAL",
                    "trace_completeness": None,
                    "codes": sorted({e["code"] for e in sel}),
                    "root_cause_id": rid,
                    "primary_error_code": primary,
                    "secondary_error_codes": secondary,
                    # Decision D3, Renxi Qiu, 22 August 2026: NO. A code whose status effect is
                    # NONE cannot change a case, so routing it to human review inflates the
                    # reported workload for something nothing depends on.
                    "human_review_required": any(
                        ont.detection(e["code"]) in ("HUMAN", "HYBRID")
                        and ont.status_effect(e["code"]) != "NONE" for e in sel),
                    "reading": reading,
                })
    return rows, errors, summaries


def metrics(summaries, level, condition, reading):
    sel = [s for s in summaries if s["audit_level"] == level
           and s["condition"] == condition and s["reading"] == reading]
    n = len(sel)
    if not n:
        return None
    return {
        "expected": n,
        "coverage": sum(s["evaluable"] for s in sel) / n,
        "reconstructibility": sum(s["reconstructible"] for s in sel) / n,
        "conformity": sum(s["case_status"] == "CONFORMANT" for s in sel) / n,
        "critical_rate": sum(s["critical"] for s in sel) / n,
    }


def per_memory(summaries, level, condition, reading, predicate):
    out = collections.defaultdict(lambda: [0, 0])
    for s in summaries:
        if s["audit_level"] == level and s["condition"] == condition and s["reading"] == reading:
            out[s["memory_id"]][1] += 1
            out[s["memory_id"]][0] += 1 if predicate(s) else 0
    return {k: tuple(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="run")
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ont = Ontology()
    rows, errors, summaries = build(work, ont)
    sp = work / "level2_b1_structural.json"
    structural_b1 = json.loads(sp.read_text()) if sp.exists() else {}

    with open(out / "audit_errors.jsonl", "w") as fh:
        for e in errors:
            fh.write(json.dumps(e) + "\n")
    with open(out / "audit_case_summaries.jsonl", "w") as fh:
        for s in summaries:
            fh.write(json.dumps(s) + "\n")

    # memory summaries
    agg = collections.defaultdict(lambda: collections.Counter())
    for s in summaries:
        k = (s["memory_id"], s["condition"], s["audit_level"], s["reading"])
        agg[k]["expected"] += 1
        agg[k]["evaluable"] += s["evaluable"]
        agg[k]["reconstructible"] += s["reconstructible"]
        agg[k]["conformant"] += s["case_status"] == "CONFORMANT"
        agg[k]["critical"] += s["critical"]
        agg[k]["not_applicable"] += s["case_status"] == "NOT_APPLICABLE"
    with open(out / "audit_memory_summaries.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["memory_id", "condition", "audit_level", "reading", "expected", "evaluable",
                    "reconstructible", "conformant", "critical", "not_applicable"])
        for (m, c, l, r), v in sorted(agg.items()):
            w.writerow([m, c, l, r, v["expected"], v["evaluable"], v["reconstructible"],
                        v["conformant"], v["critical"], v["not_applicable"]])

    # condition metrics
    with open(out / "audit_condition_metrics.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["audit_level", "condition", "reading", "expected", "coverage",
                    "reconstructibility", "conformity", "critical_rate"])
        for reading in READINGS:
            for level in ("L1_IO", "L2_M0", "L2_B1", "L2_B0"):
                for cond in ("B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY"):
                    m = metrics(summaries, level, cond, reading)
                    if m:
                        w.writerow([level, cond, reading, m["expected"],
                                    f"{m['coverage']:.6f}", f"{m['reconstructibility']:.6f}",
                                    f"{m['conformity']:.6f}", f"{m['critical_rate']:.6f}"])

    # domain and root-cause prevalence (descriptive)
    memories = sorted({r["memory_id"] for r in rows})
    dom = collections.Counter()
    for e in errors:
        dom[(e["audit_level"], e["condition"], e["domain"], e["reading"])] += 1
    with open(out / "audit_error_domains.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["audit_level", "condition", "domain", "reading", "findings"])
        for k, v in sorted(dom.items()):
            w.writerow([*k, v])

    rc = collections.Counter()
    for s in summaries:
        if s["primary_error_code"]:
            rc[(s["audit_level"], s["condition"], s["reading"], s["primary_error_code"])] += 1
    with open(out / "audit_root_causes.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["audit_level", "condition", "reading", "primary_error_code", "cases"])
        for k, v in sorted(rc.items()):
            w.writerow([*k, v])

    # matched M0 -> B1 trace-status transitions
    m0 = {(s["memory_id"], s["canonical_id"], s["rendering"], s["reading"]): s["case_status"]
          for s in summaries if s["audit_level"] == "L2_M0"}
    b1 = {(s["memory_id"], s["canonical_id"], s["rendering"], s["reading"]): s["case_status"]
          for s in summaries if s["audit_level"] == "L2_B1"}
    tm = collections.Counter()
    for k, v in m0.items():
        if k in b1:
            tm[(k[3], v, b1[k])] += 1
    with open(out / "audit_transition_matrix_M0_B1.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["reading", "m0_status", "b1_status", "cases"])
        for k, v in sorted(tm.items()):
            w.writerow([*k, v])

    # Release-integrity report, decision A4: Level 2 reported ONCE for the release, per memory,
    # not as a per-condition contrast. Protocol equation (7) is withdrawn from the confirmatory
    # set, so this file, not audit_contrasts.json, carries the Level 2 result.
    memstat = collections.defaultdict(lambda: {"m0": set(), "b1": set(), "struct": set(),
                                               "stable": set()})
    for s_ in summaries:
        if s_["reading"] != NORMATIVE_READING:
            continue
        if s_["audit_level"] == "L2_M0":
            memstat[s_["memory_id"]]["m0"].add(s_["case_status"])
        elif s_["audit_level"] == "L2_B1":
            memstat[s_["memory_id"]]["b1"].add(s_["case_status"])
            memstat[s_["memory_id"]]["struct"].add(s_["structural_status"])
    for v in structural_b1.values():
        if v.get("prospective_hash_equal") is not None:
            memstat[v["memory_id"]]["stable"].add(bool(v["prospective_hash_equal"]))
    with open(out / "audit_release_integrity.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["memory_id", "m0_trace_coherence", "b1_trace_coherence",
                    "b1_structural_status", "partial_prospective_field_stability",
                    "cases_per_memory_per_level"])
        for m in sorted(memstat):
            v = memstat[m]
            one = lambda st: (sorted(st)[0] if len(st) == 1 else "|".join(sorted(map(str, st))))
            w.writerow([m, one(v["m0"]) or "", one(v["b1"]) or "",
                        one(v["struct"]) if v["struct"] != {None} else "",
                        "STABLE" if v["stable"] == {True}
                        else ("UNSTABLE" if v["stable"] == {False} else "n/a"),
                        15])

    # primary contrasts, protocol section 13
    contrasts = {}
    conf = lambda s: s["case_status"] == "CONFORMANT"
    crit = lambda s: s["critical"]
    for reading in READINGS:
        c = {}
        c["delta_IO_B1_minus_B0"] = paired_difference(
            per_memory(summaries, "L1_IO", "B1_VERIFIED_MEMORY", reading, conf),
            per_memory(summaries, "L1_IO", "B0_LLM_ALONE", reading, conf), memories)
        c["delta_IO_B1_minus_B0_permutation"] = paired_permutation(
            per_memory(summaries, "L1_IO", "B1_VERIFIED_MEMORY", reading, conf),
            per_memory(summaries, "L1_IO", "B0_LLM_ALONE", reading, conf), memories)
        c["delta_IO_M0_minus_B0"] = paired_difference(
            per_memory(summaries, "L1_IO", "M0_OPEN_LOOP_MEMORY", reading, conf),
            per_memory(summaries, "L1_IO", "B0_LLM_ALONE", reading, conf), memories)
        c["delta_Trace_B1_minus_M0"] = paired_difference(
            per_memory(summaries, "L2_B1", "B1_VERIFIED_MEMORY", reading, conf),
            per_memory(summaries, "L2_M0", "M0_OPEN_LOOP_MEMORY", reading, conf), memories)
        c["delta_Trace_B1_minus_M0_permutation"] = paired_permutation(
            per_memory(summaries, "L2_B1", "B1_VERIFIED_MEMORY", reading, conf),
            per_memory(summaries, "L2_M0", "M0_OPEN_LOOP_MEMORY", reading, conf), memories)
        c["delta_Critical_B1_minus_M0"] = paired_difference(
            per_memory(summaries, "L2_B1", "B1_VERIFIED_MEMORY", reading, crit),
            per_memory(summaries, "L2_M0", "M0_OPEN_LOOP_MEMORY", reading, crit), memories)
        contrasts[reading] = c

    term = read_json(PKG / "contracts/terminology_audit.json")
    payload = {"label": a.label, "ontology_version": ont.version,
               "terminology": term["terminology_id"],
               "normative_reading": NORMATIVE_READING,
               "memories": len(memories), "expected_calls": len(rows),
               "endpoint_roles": {k: {"role": v["role"], "confirmatory": v["confirmatory"],
                                      "canonical_name": v["canonical_name"]}
                                  for k, v in term["estimands"].items()},
               "mandatory_caveats": [c["text"] for c in term["mandatory_caveats"].values()],
               "contrasts": contrasts}
    (out / "audit_contrasts.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps({"cases": len(rows), "errors": len(errors),
                      "case_summaries": len(summaries)}, indent=2))


if __name__ == "__main__":
    main()
