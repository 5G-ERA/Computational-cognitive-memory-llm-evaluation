#!/usr/bin/env python3
"""Protocol section 17: fixture validation and canonicalisation tests.

Requires 100% expected-status agreement on the deterministic fixtures and
exercises canonicalisation over set order, null versus empty, identifier case,
rendering-specific ordering and prohibited aliases.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Ontology, case_status, filter_reading, read_json, PKG
import audit_level1_io, audit_m0_trace, audit_b1_trace
from canonicalise_trace import (canonicalise_response, canon_identifier_set, canonical_json,
                                jaccard, norm_text, prospective_hash, sha256_obj)


class FixtureRelease:
    """Minimal stand-in for auditlib.Release, built from one fixture bundle."""

    def __init__(self, b):
        self.events = b["events"]
        self.context_map = b["context_map"]
        self.calls = {b["call"]["call_id"]: b["call"]}
        self.memory_events, self.canonical_events = {}, {}
        for e in self.events.values():
            (self.memory_events if e["scope"] == "MEMORY" else self.canonical_events) \
                .setdefault(e["owner"], set()).add(e["event_id"])
        schema = read_json(PKG.parent / "release_qa1c"
                           / "medical_assumption_memory_computational_benchmark_v0_5_1_qa1c"
                           / "public/response_schema.json") if False else None
        self.reaction_enum = {"CONTINUE_SUPPORT", "TAILOR_SUPPORT", "ESCALATE_REVIEW",
                              "WITHHOLD_ASSUMPTION", "WAIT_FOR_EVIDENCE"}
        self.rule_enum = {f"R{n:02d}_X" for n in range(0)} | {
            "R01_REVIEW_BOUNDARY", "R02_EVIDENCE_INCOMPLETE", "R03_DIFFERENT_FUNCTION",
            "R04_UNCERTAIN_FUNCTION", "R05_VERIFIED_SUCCESSOR", "R06_CONTRADICTED_PREDECESSOR",
            "R07_UNRESOLVED_VERIFICATION", "R08_PARTIALLY_CONFIRMED", "R09_SECONDARY_BARRIER",
            "R10_CONFIRMED_CONTINUATION"}

    def owner_memory(self, eid):
        e = self.events.get(eid)
        if e is None:
            return None
        if e["scope"] == "MEMORY":
            return e["owner"]
        for c in self.context_map.values():
            if c["canonical_id"] == e["owner"]:
                return c["memory_id"]
        return None


class FixtureRun:
    def __init__(self, b):
        cid = b["call"]["call_id"]
        self.raw = {cid: b["raw"]} if b["raw"] else {}
        self.parsed = {cid: b["parsed"]} if b["parsed"] else {}
        self.terminal = {cid: b["terminal"]} if b["terminal"] else {}
        self.manifest = b["run_manifest"]


def run_fixture(b, ont, contracts):
    rel, run, row = FixtureRelease(b), FixtureRun(b), b["manifest_row"]
    lvl = b["audit_level"]
    if lvl == "L1_IO":
        f = audit_level1_io.audit_case(rel, run, row, ont, contracts["L1"])
    elif lvl == "L2_M0":
        f = audit_m0_trace.audit_case(rel, run, row, ont, contracts["M0"])
    elif lvl == "L2_B1":
        m0h = {row["memory_id"]: prospective_hash(
            b["call"]["payload"].get("_m0_assumption",
                                     "The plan may not yet be understood consistently."),
            "Teach-back should improve the later account.", "PRACTICAL")}
        f = audit_b1_trace.audit_case(rel, run, row, ont, contracts["B1"], m0h)
    else:  # L2_B0
        return {"LITERAL": "NOT_APPLICABLE", "SCOPED": "NOT_APPLICABLE"}, []
    out = {r: case_status(filter_reading(f.errors, r, ont)) for r in ("LITERAL", "SCOPED")}
    return out, sorted({e["code"] for e in f.errors})


def canonicalisation_tests():
    t = []
    a, _, _, _ = canon_identifier_set(["EVT-0000002", "EVT-0000001"])
    b, _, _, _ = canon_identifier_set(["EVT-0000001", "EVT-0000002"])
    t.append({"test": "set_order_invariance", "pass": a == b})

    c = canonicalise_response({"reaction": "continue_support", "rule_id": "r10_confirmed_continuation",
                               "decisive_event_ids": ["evt-0000001"], "reason": "  x  "})
    t.append({"test": "identifier_case_normalised",
              "pass": c["reaction"] == "CONTINUE_SUPPORT" and c["rule_id"] == "R10_CONFIRMED_CONTINUATION"
                      and c["decisive_event_ids"] == ["EVT-0000001"]})
    t.append({"test": "whitespace_trimmed", "pass": c["reason"] == "x"})
    t.append({"test": "raw_value_retained", "pass": c["raw_value"]["reason"] == "  x  "})

    n = canonicalise_response({"reaction": "CONTINUE_SUPPORT", "rule_id": "R10_CONFIRMED_CONTINUATION",
                               "decisive_event_ids": [], "reason": None})
    t.append({"test": "null_versus_empty_distinguished",
              "pass": n["reason"] is None and n["decisive_event_ids"] == []})

    t.append({"test": "prohibited_alias_rejected",
              "pass": canonicalise_response(
                  {"reaction": "CONTINUE_SUPPORT", "rule_id": "R10_CONFIRMED_CONTINUATION",
                   "decisive_event_ids": [1234], "reason": "x"})["undeclared_citations"] == [1234]})

    t.append({"test": "rendering_order_invariance_of_canonical_json",
              "pass": canonical_json({"b": 1, "a": [2, 1]}) == canonical_json({"a": [2, 1], "b": 1})})
    t.append({"test": "additional_property_detected",
              "pass": canonicalise_response(
                  {"reaction": "CONTINUE_SUPPORT", "rule_id": "R10_CONFIRMED_CONTINUATION",
                   "decisive_event_ids": ["EVT-0000001"], "reason": "x",
                   "confidence": 0.9})["extra_fields"] == ["confidence"]})
    t.append({"test": "jaccard_identical_is_one", "pass": jaccard("a b c", "c b a") == 1.0})
    t.append({"test": "prospective_hash_is_whitespace_stable",
              "pass": prospective_hash(" a ", "b", "C") == prospective_hash("a", " b", "C")})
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    ont = Ontology()
    contracts = {"L1": read_json(PKG / "contracts/level1_io_contract.json"),
                 "M0": read_json(PKG / "contracts/m0_prospective_contract.json"),
                 "B1": read_json(PKG / "contracts/b1_resolved_contract.json")}
    results = []
    for p in sorted((PKG / "fixtures").rglob("*.json")):
        b = json.loads(p.read_text())
        got, codes = run_fixture(b, ont, contracts)
        status_ok = got == b["expected_case_status"]
        codes_ok = codes == b["expected_codes"]
        results.append({"fixture": b["fixture"], "path": str(p.relative_to(PKG)),
                        "audit_level": b["audit_level"],
                        "expected_status": b["expected_case_status"], "observed_status": got,
                        "expected_codes": b["expected_codes"], "observed_codes": codes,
                        "status_agreement": status_ok, "code_agreement": codes_ok,
                        "pass": status_ok and codes_ok})
    canon = canonicalisation_tests()
    report = {
        "fixtures": results,
        "fixture_count": len(results),
        "fixture_agreement": (sum(r["pass"] for r in results) / len(results)) if results else 0.0,
        "canonicalisation_tests": canon,
        "canonicalisation_pass": all(c["pass"] for c in canon),
        "pass": bool(results) and all(r["pass"] for r in results) and all(c["pass"] for c in canon),
    }
    Path(a.report).write_text(json.dumps(report, indent=2))
    print(json.dumps({"fixture_count": report["fixture_count"],
                      "fixture_agreement": report["fixture_agreement"],
                      "canonicalisation_pass": report["canonicalisation_pass"],
                      "pass": report["pass"]}, indent=2))
    for r in results:
        if not r["pass"]:
            print("FAIL", r["fixture"], "status", r["observed_status"], "codes", r["observed_codes"])
    if not report["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
