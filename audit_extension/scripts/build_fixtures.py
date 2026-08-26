#!/usr/bin/env python3
"""Generate the deterministic validation fixtures of protocol section 17.

Each fixture is a self-contained case bundle: a synthetic source-event
registry, one payload, one provider response and one manifest row, plus the
expected case status per reading and the expected deterministic error codes.
The world is synthetic and tiny so that every expected status is unambiguous.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import PKG, read_json
from canonicalise_trace import sha256_obj

def _cid(name):
    return read_json(PKG / "contracts" / name)["contract_id"]


MEM, CAN = "MEM-FIX-01", "CAN-FIX-01"
EV = {
    "EVT-9000001": {"event_id": "EVT-9000001", "event_time": "2026-08-01", "source": "patient_report",
                    "content": "Formation record for the represented support relation.",
                    "scope": "MEMORY", "owner": MEM},
    "EVT-9000002": {"event_id": "EVT-9000002", "event_time": "2026-08-08", "source": "support_record",
                    "content": "The planned support action was implemented.",
                    "scope": "MEMORY", "owner": MEM},
    "EVT-9000003": {"event_id": "EVT-9000003", "event_time": "2026-08-15", "source": "patient_report",
                    "content": "The later account improved after support.",
                    "scope": "MEMORY", "owner": MEM},
    "EVT-9000004": {"event_id": "EVT-9000004", "event_time": "2026-08-20", "source": "administrative_record",
                    "content": "Attendance was recorded but medicine use was not established.",
                    "scope": "MEMORY", "owner": MEM},
    "EVT-9000005": {"event_id": "EVT-9000005", "event_time": "2026-08-22", "source": "support_record",
                    "content": "A later alternative relation was observed.",
                    "scope": "MEMORY", "owner": MEM},
    "EVT-9000101": {"event_id": "EVT-9000101", "event_time": "2026-09-10", "source": "patient_report",
                    "content": "A previously represented difficulty is mentioned currently.",
                    "scope": "CANONICAL_CONTEXT", "owner": CAN},
    "EVT-9000102": {"event_id": "EVT-9000102", "event_time": "2026-09-11", "source": "support_record",
                    "content": "A current observation from another support source.",
                    "scope": "CANONICAL_CONTEXT", "owner": CAN},
    # exists in the registry but is never delivered: used by the invisible-citation fixture
    "EVT-9000999": {"event_id": "EVT-9000999", "event_time": "2026-09-01", "source": "support_record",
                    "content": "Registered but never delivered in any condition payload.",
                    "scope": "MEMORY", "owner": MEM},
}
LONG = ["EVT-9000001", "EVT-9000002", "EVT-9000003", "EVT-9000004", "EVT-9000005", "EVT-9000999"]
CURR = ["EVT-9000101", "EVT-9000102"]

PROSPECTIVE = {"assumption": "The plan may not yet be understood consistently.",
               "expected_consequence": "Teach-back should improve the later account.",
               "alternative": "PRACTICAL"}
RESOLVED = {"statement": "The target relation changed after support and the assessed alternative "
                         "was not established.",
            "constitutive_event_ids": ["EVT-9000002", "EVT-9000003"],
            "competing_or_unresolved_event_ids": ["EVT-9000004"],
            "scope": "understanding",
            "limitations": ["Availability does not establish medicine use."]}
GUIDE = {"relation-delta": "The current relation is comparable and no additional barrier is active."}


def records(ids):
    return [{"event_id": i, "event_time": EV[i]["event_time"], "source": EV[i]["source"],
             "content": EV[i]["content"]} for i in ids]


def payload(condition, *, long_ids=None, curr_ids=None, memory=None):
    p = {"shared_world_rules": {"world_specification_id": "MSW-0.5.1"},
         "reaction_vocabulary": ["CONTINUE_SUPPORT", "TAILOR_SUPPORT", "ESCALATE_REVIEW",
                                 "WITHHOLD_ASSUMPTION", "WAIT_FOR_EVIDENCE"],
         "current_records": records(curr_ids if curr_ids is not None else CURR),
         "condition": condition,
         "longitudinal_records": records(long_ids if long_ids is not None else LONG)}
    if condition == "M0_OPEN_LOOP_MEMORY":
        p["open_loop_memory"] = memory if memory is not None else dict(PROSPECTIVE)
    if condition == "B1_VERIFIED_MEMORY":
        p["verified_cognitive_memory"] = memory if memory is not None else {
            "memory_id": MEM, "prospective": dict(PROSPECTIVE),
            "resolved_relation": json.loads(json.dumps(RESOLVED)),
            "comparison_guide": dict(GUIDE), "successor_relation": None}
    return p


def bundle(name, level, condition, *, response, pl=None, expect_literal, expect_scoped,
           codes, finish="stop", terminal=True, parsed=True, note=""):
    pl = pl if pl is not None else payload(condition)
    call_id = "CALL-FIX-" + name.upper().replace("_", "-")[:24]
    row = {"call_id": call_id, "memory_id": MEM, "context_id": CAN + "-STR",
           "canonical_id": CAN, "condition": condition, "rendering": "STRUCTURED",
           "payload_sha256": sha256_obj(pl),
           "level1_contract": _cid("level1_io_contract.json"),
           "level2_contract": {"B0_LLM_ALONE": None,
                               "M0_OPEN_LOOP_MEMORY": _cid("m0_prospective_contract.json"),
                               "B1_VERIFIED_MEMORY": _cid("b1_resolved_contract.json")}[condition]}
    return {
        "fixture": name, "audit_level": level, "note": note,
        "events": EV,
        "context_map": {CAN + "-STR": {"canonical_id": CAN, "memory_id": MEM,
                                       "rendering": "STRUCTURED"}},
        "call": {"call_id": call_id, "memory_id": MEM, "context_id": CAN + "-STR",
                 "canonical_id": CAN, "condition": condition, "payload": pl},
        "manifest_row": row,
        "raw": {"call_id": call_id, "finish_reason": finish},
        "terminal": ({"call_id": call_id, "terminal_status": "COMPLETED_VALID",
                      "condition": condition, "memory_id": MEM} if terminal else None),
        "parsed": ({"call_id": call_id, "status": "COMPLETED_VALID", "parsed": response}
                   if parsed else None),
        "run_manifest": {"benchmark_version": "0.5.1-qa1b"},
        "expected_case_status": {"LITERAL": expect_literal, "SCOPED": expect_scoped},
        "expected_codes": sorted(codes),
    }


GOOD_L1 = {"reaction": "CONTINUE_SUPPORT", "rule_id": "R10_CONFIRMED_CONTINUATION",
           "decisive_event_ids": ["EVT-9000003", "EVT-9000101"],
           "reason": "The longitudinal record EVT-9000003 shows the represented relation held after "
                     "support, and the current record EVT-9000101 reports the same relation with no "
                     "additional barrier, so the relation remains comparable."}


def all_fixtures():
    F = []

    F.append(("conformant/level1_conformant.json", bundle(
        "level1_conformant", "L1_IO", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        expect_literal="CONFORMANT", expect_scoped="CONFORMANT", codes=[],
        note="Protocol section 17: conformant Level 1 trace.")))

    r = dict(GOOD_L1, reason="The relation remains comparable and support should continue.")
    F.append(("conformant/level1_info_only.json", bundle(
        "level1_info_only", "L1_IO", "B1_VERIFIED_MEMORY", response=r,
        expect_literal="CONFORMANT", expect_scoped="CONFORMANT",
        codes=["E4_INFLUENCE_UNEXPLAINED"],
        note=("The stated reason names no event identifier. Per decision A1, Renxi Qiu, "
              "22 August 2026, E4_INFLUENCE_UNEXPLAINED is INFO with no case-status effect, so "
              "the finding is recorded and the case remains conformant. This fixture exists to "
              "hold that demotion in place: if the severity is ever restored, it fails. "
              "Protocol section 17 also asks for an INCOMPLETE Level 1 fixture; none is "
              "constructible, because no Level 1 code carries the INCOMPLETE status effect. "
              "That coverage gap is recorded rather than faked."))))

    r = dict(GOOD_L1, reaction="CONTINUE_SUPPORT", rule_id="R10_CONFIRMED_CONTINUATION",
             decisive_event_ids=["EVT-9000003"],
             reason="EVT-9000003 shows the relation held after support.")
    F.append(("nonconformant/level1_nonconformant_citation.json", bundle(
        "level1_nonconformant_citation", "L1_IO", "B1_VERIFIED_MEMORY", response=r,
        expect_literal="NONCONFORMANT", expect_scoped="NONCONFORMANT",
        codes=["E1_CURRENT_GROUNDS_MISSING"],
        note="Current applicability asserted with no current citation.")))

    r = dict(GOOD_L1, decisive_event_ids=["EVT-9000999", "EVT-9000101"],
             reason="EVT-9000999 establishes the relation and EVT-9000101 confirms it currently.")
    F.append(("critical/level1_critical_invisible_citation.json", bundle(
        "level1_critical_invisible_citation", "L1_IO", "B1_VERIFIED_MEMORY", response=r,
        pl=payload("B1_VERIFIED_MEMORY", long_ids=[i for i in LONG if i != "EVT-9000999"]),
        expect_literal="NOT_EVALUABLE", expect_scoped="NOT_EVALUABLE",
        codes=["E0_INPUT_TRUNCATED", "E1_CITATION_NOT_VISIBLE", "E1_HISTORICAL_GROUNDS_MISSING"],
        note=("Cited event exists in the registry but was withheld from the payload. The withheld "
              "record also makes the delivered set incomplete, which is itself E0_INPUT_TRUNCATED "
              "and takes precedence in the case status."))))

    r = dict(GOOD_L1, reaction="ESCALATE_REVIEW")
    F.append(("critical/level1_critical_rule_outcome.json", bundle(
        "level1_critical_rule_outcome", "L1_IO", "B1_VERIFIED_MEMORY", response=r,
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="NONCONFORMANT_CRITICAL",
        codes=["E4_RULE_OUTCOME_INCONSISTENT"],
        note="Stated rule cannot produce the stated outcome.")))

    F.append(("conformant/m0_conformant.json", bundle(
        "m0_conformant", "L2_M0", "M0_OPEN_LOOP_MEMORY",
        response={"reaction": "WAIT_FOR_EVIDENCE", "rule_id": "R07_UNRESOLVED_VERIFICATION",
                  "decisive_event_ids": ["EVT-9000001"],
                  "reason": "EVT-9000001 records the assumption; the expected consequence is not "
                            "yet resolved by any delivered record."},
        expect_literal="NONCONFORMANT", expect_scoped="CONFORMANT",
        codes=["E1_WINDOW_INVALID", "E3_PROSPECTIVE_TRACE_INCOMPLETE", "E5_VERSION_AMBIGUOUS"],
        note=("Conformant M0 prospective trace. Under the LITERAL reading the canonical fields the "
              "parent release does not record are counted as missing mandatory components; under "
              "SCOPED they are excluded. Consequence closure is never an error for M0."))))

    F.append(("conformant/m0_open_loop_by_design.json", bundle(
        "m0_open_loop_by_design", "L2_M0", "M0_OPEN_LOOP_MEMORY",
        response={"reaction": "WAIT_FOR_EVIDENCE", "rule_id": "R07_UNRESOLVED_VERIFICATION",
                  "decisive_event_ids": ["EVT-9000102"],
                  "reason": "No delivered record resolves the expected consequence (EVT-9000102)."},
        expect_literal="NONCONFORMANT", expect_scoped="CONFORMANT",
        codes=["E1_WINDOW_INVALID", "E3_PROSPECTIVE_TRACE_INCOMPLETE", "E5_VERSION_AMBIGUOUS"],
        note=("The absent evidence-resolved consequence must NOT raise "
              "E3_CONSEQUENCE_CLOSURE_ABSENT; it is OPEN_LOOP_BY_CONDITION_DESIGN."))))

    F.append(("conformant/b1_conformant.json", bundle(
        "b1_conformant", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="CONFORMANT",
        codes=["E2_CAPABILITY_MISATTRIBUTION", "E2_FUNCTION_MISMATCH", "E2_SCOPE_OVERREACH",
               "E3_PROSPECTIVE_TRACE_INCOMPLETE", "E3_RESOLUTION_STATUS_MISSING",
               "E4_ROLE_TRACE_INCONSISTENT", "E5_VERSION_AMBIGUOUS"],
        note=("Conformant B1 resolved trace. The LITERAL codes are all "
              "NOT_RECORDED_IN_SOURCE_RELEASE field reports, which is why the LITERAL status is "
              "not CONFORMANT for any case in this parent release."))))

    m = {"memory_id": MEM, "prospective": dict(PROSPECTIVE),
         "resolved_relation": {**json.loads(json.dumps(RESOLVED)), "statement": ""},
         "comparison_guide": dict(GUIDE), "successor_relation": None}
    F.append(("critical/b1_missing_closure.json", bundle(
        "b1_missing_closure", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        pl=payload("B1_VERIFIED_MEMORY", memory=m),
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="NONCONFORMANT_CRITICAL",
        codes=["E3_CONSEQUENCE_CLOSURE_ABSENT", "E2_CAPABILITY_MISATTRIBUTION",
               "E2_FUNCTION_MISMATCH", "E2_SCOPE_OVERREACH", "E3_PROSPECTIVE_TRACE_INCOMPLETE",
               "E3_RESOLUTION_STATUS_MISSING", "E4_ROLE_TRACE_INCONSISTENT",
               "E5_VERSION_AMBIGUOUS"],
        note="B1 missing consequence closure.")))

    m = {"memory_id": MEM,
         "prospective": {**PROSPECTIVE, "assumption": "A silently rewritten formation assumption."},
         "resolved_relation": json.loads(json.dumps(RESOLVED)),
         "comparison_guide": dict(GUIDE), "successor_relation": None}
    F.append(("critical/b1_prospective_rewrite.json", bundle(
        "b1_prospective_rewrite", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        pl=payload("B1_VERIFIED_MEMORY", memory=m),
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="CONFORMANT",
        codes=["E5_PROSPECTIVE_REWRITE", "E2_CAPABILITY_MISATTRIBUTION", "E2_FUNCTION_MISMATCH",
               "E2_SCOPE_OVERREACH", "E3_PROSPECTIVE_TRACE_INCOMPLETE",
               "E3_RESOLUTION_STATUS_MISSING", "E4_ROLE_TRACE_INCONSISTENT",
               "E5_VERSION_AMBIGUOUS"],
        note=("The three recorded prospective fields differ between M0 and B1. Per decision B6, "
              "Renxi Qiu, 22 August 2026, the full non-rewrite claim is withdrawn on this parent "
              "release: the finding is reported as partial prospective field stability, is INFO, "
              "and carries no case-status effect, so the SCOPED case is conformant. The LITERAL "
              "status comes from the NOT_RECORDED field reports, not from this finding."))))

    m = {"memory_id": MEM, "prospective": dict(PROSPECTIVE),
         "resolved_relation": json.loads(json.dumps(RESOLVED)),
         "comparison_guide": dict(GUIDE),
         "successor_relation": {"statement": "A later alternative relation was observed.",
                                "provenance_event_ids": ["EVT-9000005"], "scope": "concern"}}
    F.append(("conformant/b1_successor_valid.json", bundle(
        "b1_successor_valid", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        pl=payload("B1_VERIFIED_MEMORY", memory=m),
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="CONFORMANT",
        codes=["E2_CAPABILITY_MISATTRIBUTION", "E2_FUNCTION_MISMATCH", "E2_SCOPE_OVERREACH",
               "E3_PROSPECTIVE_TRACE_INCOMPLETE", "E3_RESOLUTION_STATUS_MISSING",
               "E4_ROLE_TRACE_INCONSISTENT", "E5_VERSION_AMBIGUOUS"],
        note="Valid successor link: new evidence, distinct statement, recorded scope.")))

    m2 = json.loads(json.dumps(m))
    m2["successor_relation"]["provenance_event_ids"] = ["EVT-9000002"]
    F.append(("critical/b1_successor_invalid.json", bundle(
        "b1_successor_invalid", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        pl=payload("B1_VERIFIED_MEMORY", memory=m2),
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="NONCONFORMANT_CRITICAL",
        codes=["E5_SUCCESSOR_INVALID", "E2_CAPABILITY_MISATTRIBUTION", "E2_FUNCTION_MISMATCH",
               "E2_SCOPE_OVERREACH", "E3_PROSPECTIVE_TRACE_INCOMPLETE",
               "E3_RESOLUTION_STATUS_MISSING", "E4_ROLE_TRACE_INCONSISTENT",
               "E5_VERSION_AMBIGUOUS"],
        note="Invalid successor: provenance is a subset of the constitutive evidence, so the "
             "successor cites no new evidence.")))

    NOT_RECORDED_B1 = ["E2_CAPABILITY_MISATTRIBUTION", "E2_FUNCTION_MISMATCH",
                       "E2_SCOPE_OVERREACH", "E3_PROSPECTIVE_TRACE_INCOMPLETE",
                       "E3_RESOLUTION_STATUS_MISSING", "E4_ROLE_TRACE_INCONSISTENT",
                       "E5_VERSION_AMBIGUOUS"]

    m = {"memory_id": MEM, "prospective": dict(PROSPECTIVE),
         "resolved_relation": {**json.loads(json.dumps(RESOLVED)),
                               "statement": "Timing did not establish whether the expected "
                                            "relation occurred.",
                               "constitutive_event_ids": []},
         "comparison_guide": dict(GUIDE), "successor_relation": None}
    F.append(("conformant/b1_unresolved_by_design.json", bundle(
        "b1_unresolved_by_design", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        pl=payload("B1_VERIFIED_MEMORY", memory=m),
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="CONFORMANT",
        codes=NOT_RECORDED_B1,
        note=("Constitutive evidence is absent AND the relation positively represents "
              "unresolvedness: a statement is present and competing evidence is retained. Per "
              "decision A3, Renxi Qiu, 22 August 2026, this is "
              "UNRESOLVED_BY_CONDITION_DESIGN and must NOT raise "
              "E3_CONSTITUTIVE_LINK_MISSING, symmetric with the open-loop exemption M0 has. The "
              "LITERAL status comes only from the NOT_RECORDED field reports."))))

    m2 = json.loads(json.dumps(m))
    m2["resolved_relation"]["competing_or_unresolved_event_ids"] = []
    F.append(("critical/b1_constitutive_missing_not_represented.json", bundle(
        "b1_constitutive_missing_not_represented", "L2_B1", "B1_VERIFIED_MEMORY", response=GOOD_L1,
        pl=payload("B1_VERIFIED_MEMORY", memory=m2),
        expect_literal="NONCONFORMANT_CRITICAL", expect_scoped="NONCONFORMANT_CRITICAL",
        codes=NOT_RECORDED_B1 + ["E3_CONSTITUTIVE_LINK_MISSING"],
        note=("The other half of decision A3. Constitutive evidence is absent and the relation "
              "does NOT represent unresolvedness: no competing evidence is retained. The "
              "exemption does not apply, the relation is simply broken, and "
              "E3_CONSTITUTIVE_LINK_MISSING still fires as a critical violation. Without this "
              "fixture the A3 carve-out could silently swallow every missing constitutive "
              "link."))))

    F.append(("conformant/b0_level2_not_applicable.json", bundle(
        "b0_level2_not_applicable", "L2_B0", "B0_LLM_ALONE",
        response={"reaction": "WAIT_FOR_EVIDENCE", "rule_id": "R02_EVIDENCE_INCOMPLETE",
                  "decisive_event_ids": ["EVT-9000102"],
                  "reason": "EVT-9000102 leaves a comparison-critical current field absent."},
        expect_literal="NOT_APPLICABLE", expect_scoped="NOT_APPLICABLE", codes=[],
        note="B0 has no persistent cognitive-trace object; Level 2 is not applicable by design "
             "and is neither incomplete nor failed.")))
    return F


def main():
    root = PKG / "fixtures"
    for rel, obj in all_fixtures():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=1, sort_keys=True))
    print(json.dumps({"fixtures_written": len(all_fixtures())}, indent=2))


if __name__ == "__main__":
    main()
