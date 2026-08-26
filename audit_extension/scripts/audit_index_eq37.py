#!/usr/bin/env python3
"""The Cognitive Memory Audit Index of V4.7, equation (37), computed on Experiment 1.

    Q_audit = (1 / T_eval) * sum over evaluable boundaries t of sqrt(q_DCA,t * q_DCC,t)

Mapping onto Experiment 1, as proposed by Renxi Qiu on 22 August 2026:

  boundary t   one canonical context under one condition, delivered in three renderings
  q_DCA,t      RECONSTRUCTION quality: trace completeness of the Level 1 audit, the weighted
               proportion of valid mandatory components (protocol section 13), averaged over
               the three renderings. Oracle-free. This is the DCA side: can the grounds be
               reconstructed from what the interface exposed.
  q_DCC,t      REPLAY quality: pathway invariance, the fraction of rendering pairs that return
               the same rule_id (0, 1/3 or 1). Oracle-free. This is the DCC side: does the
               resolved pathway hold across a truth-preserving transformation.
  T_eval       the number of boundaries with all three renderings valid
  critical     a critical violation on any rendering forces sqrt(.) to 0 for that boundary,
               per the paper: "silent historical rewriting ... prevented audit conformity
               regardless of the scalar score"

Q_audit is oracle-free. The script also computes it CONDITIONED ON ERROR (oracle), to show
why a fall in Q_audit can be good news: if the fall is concentrated on erroneous boundaries,
the index is doing what DCC is for - flagging boundaries that should resolve to review.
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Release, Run, Ontology, read_json, PKG
import audit_level1_io
from calculate_clustered_intervals import paired_difference, paired_permutation

CONDS = ("B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--work", required=True, help="work dir holding audit_manifest.jsonl")
    ap.add_argument("--split", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--scoring", help="scoring_records.jsonl, ONLY for the error-conditioned view; needs inspection authorisation")
    ap.add_argument("--authorisation")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rel, run, ont = Release(Path(a.release)), Run(Path(a.run)), Ontology()
    contract = read_json(PKG / "contracts/level1_io_contract.json")
    rows = [json.loads(l) for l in open(Path(a.work) / "audit_manifest.jsonl")]

    # q_DCA per call: trace completeness; critical flag
    q_dca, critical, rule = {}, {}, {}
    for row in rows:
        f = audit_level1_io.audit_case(rel, run, row, ont, contract)
        q_dca[row["call_id"]] = f.completeness() or 0.0
        critical[row["call_id"]] = any(e["status_effect"] == "NONCONFORMANT_CRITICAL"
                                       and ont.evaluable(e["code"]) for e in f.errors)
        p = run.parsed.get(row["call_id"], {}).get("parsed")
        rule[row["call_id"]] = p.get("rule_id") if isinstance(p, dict) else None

    # boundaries
    by = collections.defaultdict(dict)
    for row in rows:
        by[(row["memory_id"], row["canonical_id"], row["condition"])][row["rendering"]] = row["call_id"]

    correct = {}
    if a.scoring:
        auth = json.loads(Path(a.authorisation).read_text())
        if "INSPECTION" not in auth.get("authorises", "").upper():
            sys.exit("authorisation does not permit inspection")
        for l in open(a.scoring):
            r = json.loads(l)
            if r.get("status") == "COMPLETED_VALID":
                correct[r["call_id"]] = bool(r["rule_correct"])

    per_mem = {c: collections.defaultdict(lambda: [0.0, 0]) for c in CONDS}
    per_mem_err = {c: collections.defaultdict(lambda: [0.0, 0]) for c in CONDS}
    per_mem_ok = {c: collections.defaultdict(lambda: [0.0, 0]) for c in CONDS}
    dropped = collections.Counter()
    detail = {c: {"q_dca": [], "q_dcc": [], "q": []} for c in CONDS}
    for (mem, canon, cond), rends in by.items():
        calls = [rends.get(r) for r in ("STRUCTURED", "CHRONOLOGICAL", "CONCISE")]
        if any(c is None or rule.get(c) is None for c in calls):
            dropped[cond] += 1
            continue
        qd = sum(q_dca[c] for c in calls) / 3.0
        rs = [rule[c] for c in calls]
        pairs = [(0, 1), (0, 2), (1, 2)]
        qc = sum(1 for i, j in pairs if rs[i] == rs[j]) / 3.0
        q = 0.0 if any(critical[c] for c in calls) else (qd * qc) ** 0.5
        per_mem[cond][mem][0] += q; per_mem[cond][mem][1] += 1
        detail[cond]["q_dca"].append(qd); detail[cond]["q_dcc"].append(qc); detail[cond]["q"].append(q)
        if correct:
            err = any(not correct.get(c, True) for c in calls)
            tgt = per_mem_err if err else per_mem_ok
            tgt[cond][mem][0] += q; tgt[cond][mem][1] += 1

    def pooled(pm):
        n = sum(v[0] for v in pm.values()); d = sum(v[1] for v in pm.values())
        return (n / d) if d else None

    out = {"label": a.label, "equation": "V4.7 (37)", "split": a.split,
           "dropped_boundaries_missing_rendering": dict(dropped),
           "by_condition": {}}
    for c in CONDS:
        out["by_condition"][c] = {
            "T_eval": sum(v[1] for v in per_mem[c].values()),
            "Q_audit": pooled(per_mem[c]),
            "mean_q_DCA": sum(detail[c]["q_dca"]) / max(len(detail[c]["q_dca"]), 1),
            "mean_q_DCC": sum(detail[c]["q_dcc"]) / max(len(detail[c]["q_dcc"]), 1),
            "Q_audit_on_erroneous_boundaries": pooled(per_mem_err[c]) if correct else None,
            "Q_audit_on_correct_boundaries": pooled(per_mem_ok[c]) if correct else None,
            "n_erroneous": sum(v[1] for v in per_mem_err[c].values()) if correct else None,
            "n_correct": sum(v[1] for v in per_mem_ok[c].values()) if correct else None,
        }
    mems = sorted({k[0] for k in by})
    A = {m: tuple(v) for m, v in per_mem["B1_VERIFIED_MEMORY"].items()}
    B = {m: tuple(v) for m, v in per_mem["B0_LLM_ALONE"].items()}
    common = [m for m in mems if m in A and m in B]
    d = paired_difference(A, B, common); p = paired_permutation(A, B, common)
    out["contrast_B1_minus_B0"] = {"Q_audit_points_x100": d, "permutation": p,
                                   "note": "paired memory-clustered bootstrap, 10,000 resamples; in percentage points of Q_audit"}
    if correct:
        Ae = {m: tuple(v) for m, v in per_mem_err["B1_VERIFIED_MEMORY"].items()}
        Be = {m: tuple(v) for m, v in per_mem_err["B0_LLM_ALONE"].items()}
        ce = [m for m in mems if m in Ae and m in Be]
        out["contrast_B1_minus_B0_on_erroneous_boundaries"] = paired_difference(Ae, Be, ce)
        Ao = {m: tuple(v) for m, v in per_mem_ok["B1_VERIFIED_MEMORY"].items()}
        Bo = {m: tuple(v) for m, v in per_mem_ok["B0_LLM_ALONE"].items()}
        co = [m for m in mems if m in Ao and m in Bo]
        out["contrast_B1_minus_B0_on_correct_boundaries"] = paired_difference(Ao, Bo, co)
    Path(a.out).write_text(json.dumps(out, indent=2))
    for c, v in out["by_condition"].items():
        print(f"{a.label} {c}: Q_audit={v['Q_audit']:.4f}  qDCA={v['mean_q_DCA']:.4f}  qDCC={v['mean_q_DCC']:.4f}  T_eval={v['T_eval']}"
              + (f"  | Q on errors={v['Q_audit_on_erroneous_boundaries']:.4f} (n={v['n_erroneous']})  on correct={v['Q_audit_on_correct_boundaries']:.4f} (n={v['n_correct']})" if correct else ""))
    print(f"B1-B0: {d['point']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}] p={p['p']:.4f}")


if __name__ == "__main__":
    main()
