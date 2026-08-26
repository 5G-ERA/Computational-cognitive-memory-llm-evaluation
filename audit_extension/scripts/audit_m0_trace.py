#!/usr/bin/env python3
"""Protocol section 7: Level 2 audit of the M0 prospective cognitive trace.

M0 consequence closure is OPEN_LOOP_BY_CONDITION_DESIGN and never produces
E3_CONSEQUENCE_CLOSURE_ABSENT. Fields the parent release does not record are
raised under reading LITERAL only; contracts/m0_prospective_contract.json
declares which fields those are and why.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Release, Run, Ontology, Findings, read_json, PKG
from canonicalise_trace import canonicalise_response, jaccard, norm_text, prospective_hash

NEAR_DUPLICATE = 0.85


def map_trace(payload):
    """Protocol section 7.1 mapping. Renames and normalises only."""
    olm = payload.get("open_loop_memory")
    if not isinstance(olm, dict):
        return None
    return {
        "trace_type": "PROSPECTIVE_OPEN_LOOP",
        "formation_assumption": norm_text(olm.get("assumption")),
        "expected_consequence": norm_text(olm.get("expected_consequence")),
        "assessed_alternative": norm_text(olm.get("alternative")),
        "unmapped_source_keys": sorted(k for k in olm
                                       if k not in ("assumption", "expected_consequence", "alternative")),
    }


def audit_case(rel: Release, run: Run, row: dict, ont: Ontology, contract: dict) -> Findings:
    f = Findings(ont, row, "L2_M0")
    call = rel.calls.get(row["call_id"])
    if call is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "no payload artefact", "M0.0")
        return f
    payload = call["payload"]
    trace = map_trace(payload)
    if trace is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "condition M0 carries no open_loop_memory object", "M0.0")
        return f

    f.trace = trace
    f.structural = "OPEN_LOOP_BY_CONDITION_DESIGN"

    # --- fields the release records ------------------------------------
    ok = bool(trace["formation_assumption"])
    f.component(ok)
    if not ok:
        f.add("E3_PROSPECTIVE_TRACE_INCOMPLETE", "formation assumption absent", "M0.2")

    ok = bool(trace["expected_consequence"])
    f.component(ok)
    if not ok:
        f.add("E3_PROSPECTIVE_TRACE_INCOMPLETE", "expected consequence absent", "M0.4")

    # expected consequence must be distinct from any delivered observation
    if trace["expected_consequence"]:
        worst = max((jaccard(trace["expected_consequence"], e.get("content"))
                     for e in payload.get("longitudinal_records", []) + payload.get("current_records", [])),
                    default=0.0)
        ok = worst < NEAR_DUPLICATE
        f.component(ok)
        if not ok:
            f.add("E2_EXPECTED_AS_REALISED",
                  "expected consequence is a near-duplicate of a delivered observation", "M0.4",
                  {"max_jaccard": round(worst, 3)})

    # the open loop must not carry a resolved consequence
    leaked = sorted(k for k in payload.get("open_loop_memory", {})
                    if k in ("resolved_relation", "constitutive_event_ids", "comparison_guide",
                             "successor_relation"))
    f.component(not leaked)
    if leaked:
        f.add("E2_EXPECTED_AS_REALISED", "the open-loop object records evidence-resolved content",
              "M0.10", {"keys": leaked})

    # the trace must reach the output: some delivered record must be cited
    parsed = run.parsed.get(row["call_id"], {}).get("parsed")
    can = canonicalise_response(parsed)
    if can.get("parseable"):
        visible = ({e["event_id"] for e in payload.get("longitudinal_records", [])}
                   | {e["event_id"] for e in payload.get("current_records", [])})
        cited = set(can.get("decisive_event_ids") or [])
        ok = bool(cited & visible)
        f.component(ok)
        if not ok:
            f.add("E3_TRACE_OUTPUT_DISCONNECTED",
                  "response cites no delivered record, so no pathway can be reconstructed", "M0.11")

    # --- fields the release does not record (LITERAL reading only) ------
    for fld in contract["fields"]:
        if fld["presence"] != "NOT_RECORDED_IN_SOURCE_RELEASE" or not fld.get("mandatory_literal"):
            continue
        code = fld.get("code", "E3_PROSPECTIVE_TRACE_INCOMPLETE")
        f.add(code, f"canonical field {fld['canonical']} is NOT_RECORDED_IN_SOURCE_RELEASE",
              "M0.field", {"canonical_field": fld["canonical"],
                           "structural_status": "NOT_RECORDED_IN_SOURCE_RELEASE"},
              reading="LITERAL")
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    rel, run, ont = Release(Path(a.release)), Run(Path(a.run)), Ontology()
    contract = read_json(PKG / "contracts/m0_prospective_contract.json")
    work = Path(a.work)
    rows = [json.loads(l) for l in open(work / "audit_manifest.jsonl")
            if json.loads(l)["condition"] == "M0_OPEN_LOOP_MEMORY"]
    n = 0
    hashes = {}
    with open(work / "level2_m0_errors.jsonl", "w") as fh:
        for row in rows:
            res = audit_case(rel, run, row, ont, contract)
            for e in res.errors:
                fh.write(json.dumps(e) + "\n")
                n += 1
            t = getattr(res, "trace", None)
            if t:
                hashes[row["memory_id"]] = prospective_hash(
                    t["formation_assumption"], t["expected_consequence"], t["assessed_alternative"])
    (work / "m0_prospective_hashes.json").write_text(json.dumps(hashes, indent=1, sort_keys=True))
    print(json.dumps({"m0_cases": len(rows), "m0_errors": n, "memories_hashed": len(hashes)}, indent=2))


if __name__ == "__main__":
    main()
