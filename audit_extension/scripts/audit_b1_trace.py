#!/usr/bin/env python3
"""Protocol section 8: Level 2 audit of the B1 evidence-resolved cognitive trace.

Requires m0_prospective_hashes.json (written by audit_m0_trace.py) for the
section 8.2 comparison, which decision B6 reports as PARTIAL PROSPECTIVE FIELD
STABILITY rather than as a non-rewrite claim.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Release, Run, Ontology, Findings, read_json, PKG
from canonicalise_trace import canonicalise_response, jaccard, norm_text, prospective_hash

NEAR_DUPLICATE = 0.85
CURRENT_USE_REACTIONS = {"CONTINUE_SUPPORT", "TAILOR_SUPPORT"}
HISTORICAL_RULES = {"R05_VERIFIED_SUCCESSOR", "R06_CONTRADICTED_PREDECESSOR",
                    "R07_UNRESOLVED_VERIFICATION", "R08_PARTIALLY_CONFIRMED",
                    "R09_SECONDARY_BARRIER", "R10_CONFIRMED_CONTINUATION"}


def map_trace(payload):
    """Protocol section 8.1 mapping. Renames and normalises only."""
    m = payload.get("verified_cognitive_memory")
    if not isinstance(m, dict):
        return None
    pro, res = m.get("prospective") or {}, m.get("resolved_relation") or {}
    return {
        "trace_type": "EVIDENCE_RESOLVED_SINGLE_CANDIDATE_DCC",
        "memory_id": m.get("memory_id"),
        "formation_assumption": norm_text(pro.get("assumption")),
        "expected_consequence": norm_text(pro.get("expected_consequence")),
        "assessed_alternative": norm_text(pro.get("alternative")),
        "resolved_consequence_statement": norm_text(res.get("statement")),
        "constitutive_event_ids": list(res.get("constitutive_event_ids") or []),
        "competing_event_ids": list(res.get("competing_or_unresolved_event_ids") or []),
        "semantic_scope_label": norm_text(res.get("scope")),
        "limitations": list(res.get("limitations") or []),
        "comparison_guide": m.get("comparison_guide") or {},
        "successor_relation": m.get("successor_relation"),
    }


def audit_case(rel: Release, run: Run, row: dict, ont: Ontology, contract: dict,
               m0_hashes: dict) -> Findings:
    f = Findings(ont, row, "L2_B1")
    call = rel.calls.get(row["call_id"])
    if call is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "no payload artefact", "B1.0")
        return f
    payload = call["payload"]
    t = map_trace(payload)
    if t is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "condition B1 carries no verified_cognitive_memory object", "B1.0")
        return f
    f.trace = t

    mem = row["memory_id"]
    reg = rel.events
    vis_long = {e["event_id"] for e in payload.get("longitudinal_records", [])}
    vis_curr = {e["event_id"] for e in payload.get("current_records", [])}
    visible = vis_long | vis_curr

    # ------------------------------------------------- 8.2 non-rewrite
    h_b1 = prospective_hash(t["formation_assumption"], t["expected_consequence"],
                            t["assessed_alternative"])
    h_m0 = m0_hashes.get(mem)
    if h_m0 is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "no M0 prospective hash for this memory", "B1.2")
    else:
        # Decision B6, Renxi Qiu, 22 August 2026: PARTIAL PROSPECTIVE FIELD STABILITY. The full
        # non-rewrite claim is withdrawn on this release; three of equation (1)'s five operands
        # are not recorded, so an inequality here is reported, not treated as a violation.
        ok = h_b1 == h_m0
        f.prospective_hash_equal = ok
        f.component(ok)
        if not ok:
            f.add("E5_PROSPECTIVE_REWRITE",
                  "the three recorded prospective fields differ between the M0 and B1 objects for "
                  "this memory; reported as partial field stability, not as a non-rewrite "
                  "violation", "B1.2",
                  {"m0": h_m0[:16], "b1": h_b1[:16],
                   "operands_covered": 3, "operands_in_equation_1": 5})

    # ------------------------------------------------- 8.3 closure
    ok = bool(t["resolved_consequence_statement"])
    f.component(ok)
    if not ok:
        f.add("E3_CONSEQUENCE_CLOSURE_ABSENT", "no resolved consequence statement", "B1.3.2")

    con = t["constitutive_event_ids"]

    # Decision A3, Renxi Qiu, 22 August 2026. A relation that POSITIVELY REPRESENTS
    # unresolvedness has no constitutive evidence because it was never resolved; that is its
    # content. Symmetric with the OPEN_LOOP_BY_CONDITION_DESIGN exemption M0 already has.
    # Detector reads the delivered memory object alone: no decision-adjacent field is consulted.
    unresolved_by_design = (not con
                            and bool(t["competing_event_ids"])
                            and bool(t["resolved_consequence_statement"]))
    if unresolved_by_design:
        f.structural = "UNRESOLVED_BY_CONDITION_DESIGN"
    else:
        f.component(bool(con))
        if not con:
            f.add("E3_CONSTITUTIVE_LINK_MISSING",
                  "resolved consequence cites no constitutive event and does not represent "
                  "unresolvedness", "B1.3.4")
        bad_owner = sorted(e for e in con if reg.get(e, {}).get("owner") != mem)
        f.component(not bad_owner)
        if bad_owner:
            f.add("E3_CONSTITUTIVE_LINK_MISSING",
                  "constitutive event does not exist or does not belong to the memory", "B1.3.5",
                  {"events": bad_owner})
        not_vis = sorted(e for e in con if e not in visible)
        f.component(not not_vis)
        if not_vis:
            f.add("E1_CITATION_NOT_VISIBLE", "constitutive event is not delivered in the payload",
                  "B1.3.6", {"events": not_vis})

    # resolution time must follow formation
    if con and all(e in reg for e in con):
        res_t = max(reg[e]["event_time"] for e in con)
        form_t = min((reg[e]["event_time"] for e in vis_long if e in reg), default=None)
        ok = form_t is None or res_t >= form_t
        f.component(ok)
        if not ok:
            f.add("E1_TEMPORAL_ORDER_INVALID", "resolution time precedes formation", "B1.3.3",
                  {"resolution": res_t, "formation": form_t})

    # expected consequence must not be copied into the resolved field
    if t["expected_consequence"] and t["resolved_consequence_statement"]:
        j = jaccard(t["expected_consequence"], t["resolved_consequence_statement"])
        ok = j < NEAR_DUPLICATE
        f.component(ok)
        if not ok:
            f.add("E2_EXPECTED_AS_REALISED",
                  "resolved statement is a near-duplicate of the expected consequence", "B1.3.9",
                  {"jaccard": round(j, 3)})

    # unresolved evidence must not be represented as resolved
    overlap = sorted(set(con) & set(t["competing_event_ids"]))
    f.component(not overlap)
    if overlap:
        f.add("E2_UNRESOLVED_COLLAPSED",
              "an event recorded as competing or unresolved is also recorded as constitutive",
              "B1.3.10", {"events": overlap})

    # ------------------------------------------------- 8.4 competing evidence
    bad_comp = sorted(e for e in t["competing_event_ids"]
                      if e not in reg or reg[e]["owner"] != mem or e not in visible)
    if bad_comp:
        f.add("E1_PROVENANCE_INCOMPLETE",
              "competing or unresolved event is unregistered, foreign to the memory, or not "
              "delivered", "B1.4", {"events": bad_comp})

    # ------------------------------------------------- 8.6 current-use coherence
    can = canonicalise_response(run.parsed.get(row["call_id"], {}).get("parsed"))
    if can.get("parseable"):
        reaction, rule = can.get("reaction"), can.get("rule_id")
        cited = set(can.get("decisive_event_ids") or [])
        if reaction in CURRENT_USE_REACTIONS:
            ok = bool(cited & vis_curr)
            f.component(ok)
            if not ok:
                f.add("E3_CURRENT_USE_GROUNDS_MISSING",
                      "current use asserted with no cited current record", "B1.6.3",
                      {"reaction": reaction})
        if rule in HISTORICAL_RULES:
            named = set(con) | set(t["competing_event_ids"])
            succ = t["successor_relation"] or {}
            named |= set(succ.get("provenance_event_ids") or [])
            ok = bool(cited & (named | vis_long))
            f.component(ok)
            if not ok:
                f.add("E3_TRACE_OUTPUT_DISCONNECTED",
                      "historical rule invoked without citing any event the retained trace names",
                      "B1.6.4", {"rule": rule, "cited": sorted(cited)})
        # a successor-provenance event used as predecessor evidence under R06
        if rule == "R06_CONTRADICTED_PREDECESSOR" and t["successor_relation"]:
            sp = set((t["successor_relation"] or {}).get("provenance_event_ids") or [])
            hist_cited = cited & vis_long
            if hist_cited and hist_cited <= sp:
                f.add("E1_TEMPORAL_ORDER_INVALID",
                      "successor-provenance event cited as predecessor evidence under R06",
                      "B1.6.5", {"events": sorted(hist_cited)})

    # ------------------------------------------------- 8.7 historical integrity
    succ = t["successor_relation"]
    if succ:
        f.component(bool(t["resolved_consequence_statement"]))
        if not t["resolved_consequence_statement"]:
            f.add("E5_PREDECESSOR_OVERWRITTEN",
                  "a successor is declared but the predecessor resolved relation is not retained",
                  "B1.7.2")
        distinct = norm_text(succ.get("statement")) not in (None, "", t["resolved_consequence_statement"])
        f.component(distinct)
        if not distinct:
            f.add("E5_SUCCESSOR_INVALID", "successor statement is empty or identical to the "
                  "predecessor statement", "B1.7.3")
        prov = list(succ.get("provenance_event_ids") or [])
        new_ev = bool(prov) and not set(prov) <= set(con)
        registered = all(e in reg and reg[e]["owner"] == mem for e in prov)
        f.component(new_ev and registered)
        if not new_ev:
            f.add("E5_SUCCESSOR_INVALID", "successor cites no new evidence", "B1.7.4",
                  {"provenance": prov, "constitutive": con})
        elif not registered:
            f.add("E5_SUCCESSOR_INVALID", "successor provenance is unregistered or foreign to the "
                  "memory", "B1.7.4", {"provenance": prov})
        ok = bool(norm_text(succ.get("scope")))
        f.component(ok)
        if not ok:
            f.add("E5_SUCCESSOR_INVALID", "successor records no scope", "B1.7.3")

    # current-use content must not appear inside the immutable historical fields
    hist_blob = " ".join(filter(None, [t["resolved_consequence_statement"],
                                       t["formation_assumption"]] + [str(x) for x in t["limitations"]]))
    leaked = sorted(r for r in CURRENT_USE_REACTIONS | {"ESCALATE_REVIEW", "WITHHOLD_ASSUMPTION",
                                                        "WAIT_FOR_EVIDENCE"}
                    if r in hist_blob)
    f.component(not leaked)
    if leaked:
        f.add("E5_CURRENT_ROLE_HISTORICISED",
              "a current-use outcome label appears inside an immutable historical field", "B1.7.6",
              {"labels": leaked})

    # ------------------------------------------------- fields not recorded
    for fld in contract["fields"]:
        if fld["presence"] != "NOT_RECORDED_IN_SOURCE_RELEASE" or not fld.get("mandatory_literal"):
            continue
        f.add(fld.get("code", "E3_PROSPECTIVE_TRACE_INCOMPLETE"),
              f"canonical field {fld['canonical']} is NOT_RECORDED_IN_SOURCE_RELEASE", "B1.field",
              {"canonical_field": fld["canonical"],
               "structural_status": "NOT_RECORDED_IN_SOURCE_RELEASE"}, reading="LITERAL")
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    rel, run, ont = Release(Path(a.release)), Run(Path(a.run)), Ontology()
    contract = read_json(PKG / "contracts/b1_resolved_contract.json")
    work = Path(a.work)
    m0_hashes = json.loads((work / "m0_prospective_hashes.json").read_text())
    rows = [r for r in (json.loads(l) for l in open(work / "audit_manifest.jsonl"))
            if r["condition"] == "B1_VERIFIED_MEMORY"]
    n = 0
    structural = {}
    with open(work / "level2_b1_errors.jsonl", "w") as fh:
        for row in rows:
            res = audit_case(rel, run, row, ont, contract, m0_hashes)
            for e in res.errors:
                fh.write(json.dumps(e) + "\n")
                n += 1
            structural[row["call_id"]] = {
                "memory_id": row["memory_id"],
                "structural_status": getattr(res, "structural", None),
                "prospective_hash_equal": getattr(res, "prospective_hash_equal", None),
            }
    (work / "level2_b1_structural.json").write_text(json.dumps(structural, indent=1, sort_keys=True))
    unresolved = sorted({v["memory_id"] for v in structural.values()
                         if v["structural_status"] == "UNRESOLVED_BY_CONDITION_DESIGN"})
    stable = sorted({v["memory_id"] for v in structural.values()
                     if v["prospective_hash_equal"] is True})
    print(json.dumps({"b1_cases": len(rows), "b1_errors": n,
                      "memories_unresolved_by_condition_design": unresolved,
                      "memories_with_stable_prospective_fields": len(stable)}, indent=2))


if __name__ == "__main__":
    main()
