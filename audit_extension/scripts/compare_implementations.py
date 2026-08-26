#!/usr/bin/env python3
"""Protocol section 17: compare two independent implementations.

    python3 compare_implementations.py \
        --reference results/dev_terra --candidate <validator_out>/dev_terra \
        --reference results/dev_qwen3 --candidate <validator_out>/dev_qwen3 \
        --report validation/implementation_agreement.json

Compares only the four dimensions contracts/agreement_contract.json names as
must-agree, and ignores everything that contract puts out of scope. Both sides
supply `audit_errors.jsonl` and `audit_case_summaries.jsonl` written to
schemas/audit_error.schema.json and schemas/audit_case_summary.schema.json.

The reference implementation is not privileged: a disagreement is reported as a
disagreement, with the offending cases named, and it is for the two implementers
to decide which side is wrong.
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import read_json, PKG

DIMENSIONS = ("error_codes", "critical_status", "case_status", "aggregate_counts")
MAX_EXAMPLES = 25


def load(d: Path):
    errs = [json.loads(l) for l in open(d / "audit_errors.jsonl")]
    cases = [json.loads(l) for l in open(d / "audit_case_summaries.jsonl")]
    return errs, cases


def index(errs, cases):
    codes = collections.defaultdict(set)
    for e in errs:
        codes[(e["call_id"], e["audit_level"], e["reading"])].add(e["code"])
    status, crit, agg = {}, {}, collections.Counter()
    for c in cases:
        k = (c["call_id"], c["audit_level"], c["reading"])
        status[k] = c["case_status"]
        crit[k] = bool(c["critical"])
        a = (c["audit_level"], c["condition"], c["reading"])
        agg[(a, "expected")] += 1
        agg[(a, "evaluable")] += bool(c["evaluable"])
        agg[(a, "reconstructible")] += bool(c["reconstructible"])
        agg[(a, "conformant")] += c["case_status"] == "CONFORMANT"
        agg[(a, "critical")] += bool(c["critical"])
    return codes, status, crit, agg


def reading_view(codes, reading, ont_evaluable):
    """Fold BOTH rows into the requested reading, applying the SCOPED drop rule."""
    out = collections.defaultdict(set)
    for (cid, lvl, r), cs in codes.items():
        if r not in ("BOTH", reading):
            continue
        for code in cs:
            if reading == "SCOPED" and not ont_evaluable.get(code, True):
                continue
            out[(cid, lvl, reading)].add(code)
    return out


def compare_pair(ref: Path, cand: Path, ont_evaluable):
    r_e, r_c = load(ref)
    c_e, c_c = load(cand)
    r_codes, r_status, r_crit, r_agg = index(r_e, r_c)
    c_codes, c_status, c_crit, c_agg = index(c_e, c_c)

    result = {"reference": str(ref), "candidate": str(cand), "dimensions": {}}

    # error codes, per reading, folded the way the agreement contract specifies
    dis = []
    for reading in ("LITERAL", "SCOPED"):
        rv = reading_view(r_codes, reading, ont_evaluable)
        cv = reading_view(c_codes, reading, ont_evaluable)
        for k in sorted(set(rv) | set(cv)):
            if rv.get(k, set()) != cv.get(k, set()):
                dis.append({"key": list(k),
                            "reference_only": sorted(rv.get(k, set()) - cv.get(k, set())),
                            "candidate_only": sorted(cv.get(k, set()) - rv.get(k, set()))})
    result["dimensions"]["error_codes"] = {
        "compared": len(set(r_codes) | set(c_codes)),
        "disagreements": len(dis), "examples": dis[:MAX_EXAMPLES],
        "agree": not dis}

    for name, rd, cd in (("critical_status", r_crit, c_crit),
                         ("case_status", r_status, c_status)):
        keys = sorted(set(rd) | set(cd), key=lambda x: (x[0], x[1], x[2]))
        d = [{"key": list(k), "reference": rd.get(k), "candidate": cd.get(k)}
             for k in keys if rd.get(k) != cd.get(k)]
        result["dimensions"][name] = {"compared": len(keys), "disagreements": len(d),
                                      "examples": d[:MAX_EXAMPLES], "agree": not d}

    keys = sorted(set(r_agg) | set(c_agg), key=str)
    d = [{"key": [list(k[0]), k[1]], "reference": r_agg.get(k, 0), "candidate": c_agg.get(k, 0)}
         for k in keys if r_agg.get(k, 0) != c_agg.get(k, 0)]
    result["dimensions"]["aggregate_counts"] = {"compared": len(keys), "disagreements": len(d),
                                                "examples": d[:MAX_EXAMPLES], "agree": not d}

    result["agree"] = all(result["dimensions"][x]["agree"] for x in DIMENSIONS)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", action="append", required=True)
    ap.add_argument("--candidate", action="append", required=True)
    ap.add_argument("--validator", default="unnamed independent implementation")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    if len(a.reference) != len(a.candidate):
        sys.exit("pass one --candidate for each --reference, in the same order")

    import yaml
    ont = yaml.safe_load((PKG / "contracts/error_ontology.yaml").read_text())
    ont_evaluable = {k: bool(v.get("evaluable_in_v0_5_1_qa1c", True))
                     for k, v in ont["codes"].items()}
    contract = read_json(PKG / "contracts/agreement_contract.json")

    pairs = [compare_pair(Path(r), Path(c), ont_evaluable)
             for r, c in zip(a.reference, a.candidate)]
    agree = all(p["agree"] for p in pairs)
    report = {
        "requirement": ("Protocol section 17: a second independent validator must reproduce "
                        "deterministic error codes, critical status, case status and aggregate "
                        "counts."),
        "agreement_contract": contract["contract_id"],
        "validator": a.validator,
        "runs_compared": len(pairs),
        "comparisons": pairs,
        "out_of_scope": [x["item"] for x in contract["out_of_scope_for_agreement"]],
        "status": "SATISFIED" if agree else "NOT_SATISFIED",
        "blocks_gate_condition": "independent_validator_agreement_100pc",
    }
    Path(a.report).write_text(json.dumps(report, indent=2))
    print(json.dumps({"status": report["status"],
                      "per_run": [{"candidate": p["candidate"], "agree": p["agree"],
                                   "disagreements": {k: p["dimensions"][k]["disagreements"]
                                                     for k in DIMENSIONS}} for p in pairs]},
                     indent=2))
    if not agree:
        sys.exit(1)


if __name__ == "__main__":
    main()
