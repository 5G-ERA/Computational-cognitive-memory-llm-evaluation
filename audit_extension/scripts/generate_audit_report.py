#!/usr/bin/env python3
"""Protocol section 12: audit_report.md, the human-readable release report."""
from __future__ import annotations
import argparse, collections, csv, json, sys
from pathlib import Path


def table(rows, head):
    w = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    out = ["| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head)) + " |",
           "|" + "|".join("-" * (x + 2) for x in w) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")
    return "\n".join(out)


def pct(x):
    try:
        return f"{100 * float(x):.2f}%"
    except (TypeError, ValueError):
        return "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--repro")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    R = Path(a.results)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from auditlib import read_json, PKG
    term = read_json(PKG / "contracts/terminology_audit.json")
    CANON = {("L1_IO", "conformity"): term["metrics"]["conformity_at_L1_IO"]["canonical_name"],
             ("L2_M0", "conformity"): term["metrics"]["conformity_at_L2"]["canonical_name"],
             ("L2_B1", "conformity"): term["metrics"]["conformity_at_L2"]["canonical_name"]}

    metrics = list(csv.DictReader(open(R / "audit_condition_metrics.csv")))
    contrasts = json.loads((R / "audit_contrasts.json").read_text())
    domains = list(csv.DictReader(open(R / "audit_error_domains.csv")))
    roots = list(csv.DictReader(open(R / "audit_root_causes.csv")))
    trans = list(csv.DictReader(open(R / "audit_transition_matrix_M0_B1.csv")))

    L = [f"# Experiment 1 audit extension — audit report",
         "",
         f"Run label: **{a.label}**  ",
         f"Parent release: v0.5.1-qa1c  ",
         f"Ontology: {contrasts['ontology_version']}  ",
         f"Memory groups: {contrasts['memories']}  Expected calls: {contrasts['expected_calls']}",
         "",
         "Decision performance is not read anywhere in this report. The audit pipeline cannot open",
         "the hidden reaction, the hidden rule, the correctness label or the scoring records; the",
         "oracle guard in scripts/auditlib.py exits rather than read them.",
         "",
         "**Terminology.** Per decision B10, *audit conformity* is reserved for theory equation",
         "(36), the lifecycle certificate test, and is not used here. The Level 1 outcome is",
         f"**{CANON[('L1_IO', 'conformity')]}**; the Level 2 outcome is",
         f"**{CANON[('L2_B1', 'conformity')]}**; the section 13 reconstructibility metric is",
         f"**{term['metrics']['reconstructibility']['canonical_name']}**.",
         "",
         "**Readings.** Per decision A5, **SCOPED is normative** and LITERAL is a declared",
         "sensitivity that must never appear as a headline figure. SCOPED excludes canonical fields",
         "the parent release does not record; LITERAL counts them as missing components.",
         "",
         "**Mandatory caveats.**",
         ""] + [f"- {c['text']}" for c in term["mandatory_caveats"].values()] + [
         "",
         "## 1. Condition metrics (protocol section 13)",
         ""]

    for reading in ("SCOPED", "LITERAL"):
        rows = [[m["audit_level"], m["condition"], m["expected"], pct(m["coverage"]),
                 pct(m["reconstructibility"]), pct(m["conformity"]), pct(m["critical_rate"])]
                for m in metrics if m["reading"] == reading]
        tag = "NORMATIVE" if reading == "SCOPED" else "SENSITIVITY ONLY"
        L += [f"### Reading: {reading} ({tag})", "",
              table(rows, ["level", "condition", "expected", "audit coverage",
                           "functional auditability", "trace reconstructibility / coherence",
                           "critical rate"]), ""]

    L += ["## 2. Contrasts (protocol section 13, equations 6-8)", "",
          "Paired memory-clustered bootstrap, 10,000 resamples, two-sided 95% percentile interval.",
          "Percentage points. **No contrast in this table is confirmatory.** Per decision A2 the",
          "Level 1 differences are instrument-integrity endpoints; per decision A4 equation (7) is",
          "withdrawn from the confirmatory set and the Level 2 result is carried by",
          "`audit_release_integrity.csv`, not by this table.", ""]
    for reading in ("SCOPED", "LITERAL"):
        c = contrasts["contrasts"][reading]
        rows = []
        for k in ("delta_IO_B1_minus_B0", "delta_IO_M0_minus_B0", "delta_Trace_B1_minus_M0",
                  "delta_Critical_B1_minus_M0"):
            v = c[k]
            role = term["estimands"].get(k, {}).get("role", "")
            rows.append([k, role, f"{v['point']:+.2f}", f"[{v['lo']:+.2f}, {v['hi']:+.2f}]",
                         v["clusters"], v["resamples"]])
        for k in ("delta_IO_B1_minus_B0_permutation", "delta_Trace_B1_minus_M0_permutation"):
            v = c[k]
            rows.append([k, "ROBUSTNESS", f"p = {v['p']:.4f}", f"|obs| = {v['observed']:.2f}",
                         v["clusters"], ""])
        L += [f"### Reading: {reading}", "",
              table(rows, ["contrast", "role", "point", "95% interval", "clusters",
                           "usable resamples"]), ""]

    L += ["## 3. Parent-domain prevalence (descriptive)", ""]
    agg = collections.Counter()
    for d in domains:
        agg[(d["reading"], d["audit_level"], d["domain"])] += int(d["findings"])
    rows = [[k[0], k[1], k[2], v] for k, v in sorted(agg.items())]
    L += [table(rows, ["reading", "level", "domain", "findings"]), ""]

    L += ["## 4. Root causes (primary code only, protocol section 11)", ""]
    rows = [[r["reading"], r["audit_level"], r["condition"], r["primary_error_code"], r["cases"]]
            for r in roots]
    L += [table(rows, ["reading", "level", "condition", "primary code", "cases"]) if rows
          else "_No root causes recorded._", ""]

    L += ["## 5. Matched M0 to B1 trace-status transitions", ""]
    rows = [[t["reading"], t["m0_status"], t["b1_status"], t["cases"]] for t in trans]
    L += [table(rows, ["reading", "M0 status", "B1 status", "cases"]) if rows
          else "_No matched transitions._", ""]

    rip = R / "audit_release_integrity.csv"
    if rip.exists():
        ri = list(csv.DictReader(open(rip)))
        struct = collections.Counter(r["b1_structural_status"] or "-" for r in ri)
        stab = collections.Counter(r["partial_prospective_field_stability"] for r in ri)
        L += ["## 6. Release integrity (decision A4: the Level 2 result)", "",
              "Level 2 reported once for the release, one row per memory, under the normative",
              "SCOPED reading. Protocol equation (7) is withdrawn from the confirmatory set.", "",
              table([[r["memory_id"], r["m0_trace_coherence"], r["b1_trace_coherence"],
                      r["b1_structural_status"] or "-",
                      r["partial_prospective_field_stability"]] for r in ri],
                    ["memory", "M0 trace coherence", "B1 trace coherence",
                     "B1 structural status", "partial prospective field stability"]), "",
              f"Memories: {len(ri)}. B1 structural statuses: "
              + ", ".join(f"{k} {v}" for k, v in sorted(struct.items())) + ". "
              + "Partial prospective field stability: "
              + ", ".join(f"{k} {v}" for k, v in sorted(stab.items())) + ".",
              "", "Partial prospective field stability covers three of the five operands of",
              "protocol equation (1); per decision B6 it does not establish that no silent",
              "prospective rewrite occurred.", ""]

    if a.repro and Path(a.repro).exists():
        rp = json.loads(Path(a.repro).read_text())
        rs = rp["representation_stability"]
        L += ["## 7. Existing-data reproducibility (protocol section 14)", "",
              f"Representation stability over {rs['memories']} memories: prospective invariant "
              f"**{rs['prospective_invariant']}**, resolved invariant **{rs['resolved_invariant']}**.", ""]
        rows = [[k, v["canonical_contexts"], pct(v["reaction_exact_agreement"]),
                 pct(v["rule_exact_agreement"]), pct(v["citation_set_exact_agreement"]),
                 f"{v['citation_jaccard_mean']:.3f}" if v["citation_jaccard_mean"] is not None else "n/a"]
                for k, v in sorted(rp["cross_rendering_response_consistency"].items())]
        L += ["Cross-rendering response consistency (presentation stability, not repeated-call "
              "reproducibility):", "",
              table(rows, ["condition", "canonical contexts", "reaction agreement",
                           "rule agreement", "citation set exact", "citation Jaccard"]), ""]

    L += ["## 8. Reporting boundary", "",
          "Prediction accuracy and audit results are joined only after both analyses are frozen",
          "(protocol section 15). This report contains no accuracy figure and no join.", ""]
    Path(a.out).write_text("\n".join(L) + "\n")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
