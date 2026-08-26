#!/usr/bin/env python3
"""Protocol section 6: Level 1 input-output trace audit.

Applied to B0, M0 and B1. Reads only the visible payload, the immutable
provider response, the terminal record, the parsed record, the public schemas
and the source-event registry. It never reads the hidden reaction, the hidden
rule, the correctness label or any condition-level performance summary.

Importable: audit_case(rel, run, row, ont, contract) -> Findings
Standalone: writes results/level1_errors.jsonl for one run.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Release, Run, Ontology, Findings, read_json, PKG
from canonicalise_trace import canonicalise_response, norm_text, sha256_obj

EVT_IN_TEXT = re.compile(r"EVT-[0-9]{7}")
# L1-IO-1.3: only sources that actually occur in the registry. "authorised_review" is in the
# public observation dictionary but is never an event source, so it could only ever produce a
# false positive - and did, matching "authorised-review boundary" from the rule vocabulary.
SOURCE_TOKENS = ("patient_report", "support_record", "administrative_record")


def _clause_around(text, start, end, win=80):
    """The clause containing the identifier, not the raw character window.

    L1-IO-1.3: a source named in an adjacent clause about a different record is not an
    attribution of this identifier. Truncate at the nearest sentence or clause boundary.
    """
    lo, hi = max(0, start - win), end + win
    left, right = text[lo:start], text[end:hi]
    cut = max(left.rfind(". "), left.rfind("; "))
    if cut >= 0:
        left = left[cut + 2:]
    cuts = [x for x in (right.find(". "), right.find("; ")) if x >= 0]
    if cuts:
        right = right[:min(cuts)]
    return (left + text[start:end] + right).lower()

# Rules that assert a relation established in the longitudinal record.
HISTORICAL_RULES = {"R05_VERIFIED_SUCCESSOR", "R06_CONTRADICTED_PREDECESSOR",
                    "R07_UNRESOLVED_VERIFICATION", "R08_PARTIALLY_CONFIRMED",
                    "R09_SECONDARY_BARRIER", "R10_CONFIRMED_CONTINUATION"}
# Reactions that assert the memory is applicable to the current situation.
CURRENT_USE_REACTIONS = {"CONTINUE_SUPPORT", "TAILOR_SUPPORT"}
DEFERRAL_RULES = {"R02_EVIDENCE_INCOMPLETE", "R04_UNCERTAIN_FUNCTION", "R07_UNRESOLVED_VERIFICATION"}
WITHHOLD_RULES = {"R03_DIFFERENT_FUNCTION", "R06_CONTRADICTED_PREDECESSOR"}


def _payload_blocks(payload):
    long_ = payload.get("longitudinal_records", [])
    curr = payload.get("current_records", [])
    return (long_, curr,
            {e["event_id"] for e in long_},
            {e["event_id"] for e in curr})


def audit_case(rel: Release, run: Run, row: dict, ont: Ontology, contract: dict) -> Findings:
    f = Findings(ont, row, "L1_IO")
    cid = row["call_id"]
    call = rel.calls.get(cid)

    # ---------------------------------------------------------- 6.1 integrity
    if call is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "no payload artefact for the expected call", "L1.1.1")
        return f
    f.component(sha256_obj(call["payload"]) == row["payload_sha256"])
    if sha256_obj(call["payload"]) != row["payload_sha256"]:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "payload hash does not match the manifest", "L1.1.1")

    raw, parsed_rec, term = run.raw.get(cid), run.parsed.get(cid), run.terminal.get(cid)
    if raw is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "no immutable provider response", "L1.1.2")
    if term is None:
        f.add("E0_TERMINAL_MISSING", "no terminal-status record", "L1.1.3")
    if parsed_rec is None:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "no parsed-response record and no parser-failure status", "L1.1.4")
    f.component(raw is not None and term is not None and parsed_rec is not None)
    if raw is None or term is None or parsed_rec is None:
        return f

    # identifiers agree across artefacts
    ctx = rel.context_map[row["context_id"]]
    agree = (call["memory_id"] == row["memory_id"] == term.get("memory_id")
             and call["condition"] == row["condition"] == term.get("condition")
             and call["context_id"] == row["context_id"]
             and ctx["memory_id"] == row["memory_id"]
             and ctx["rendering"] == row["rendering"])
    f.component(agree)
    if not agree:
        f.add("E0_AUDIT_ARTEFACT_MISSING", "call, memory, context, condition or rendering "
              "identifiers disagree across artefacts", "L1.1.5",
              {"manifest": {k: row[k] for k in ("memory_id", "condition", "context_id", "rendering")},
               "terminal": {k: term.get(k) for k in ("memory_id", "condition")}})

    long_recs, curr_recs, vis_long, vis_curr = _payload_blocks(call["payload"])
    visible = vis_long | vis_curr

    # payload event identifiers unique and registered, and owned by the memory
    dup = len(visible) != len(long_recs) + len(curr_recs)
    unregistered = sorted(e for e in visible if e not in rel.events)
    f.component(not dup and not unregistered)
    if dup:
        f.add("E1_CITATION_NONEXISTENT", "duplicate event identifier in the delivered payload", "L1.1.6")
    if unregistered:
        f.add("E1_CITATION_NONEXISTENT", "delivered event absent from the source-event registry",
              "L1.1.6", {"events": unregistered[:10]})
    misowned = sorted(e for e in vis_long if rel.events.get(e, {}).get("owner") != row["memory_id"])
    misowned += sorted(e for e in vis_curr if rel.events.get(e, {}).get("owner") != row["canonical_id"])
    f.component(not misowned)
    if misowned:
        f.add("E1_CITATION_NONEXISTENT", "delivered event does not belong to the declared memory "
              "or canonical context", "L1.1.7", {"events": misowned[:10]})

    # timestamps parseable and nondecreasing within each delivered block
    def times_ok(recs):
        ts = []
        for e in recs:
            t = e.get("event_time")
            if not isinstance(t, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
                return False, None
            ts.append(t)
        return all(a <= b for a, b in zip(ts, ts[1:])), (max(ts) if ts else None)

    lo_ok, _ = times_ok(long_recs)
    cu_ok, boundary = times_ok(curr_recs)
    f.component(lo_ok and cu_ok)
    if not (lo_ok and cu_ok):
        f.add("E1_TEMPORAL_ORDER_INVALID", "delivered event times unparseable or not nondecreasing",
              "L1.1.8")

    # scientific truncation of the request
    complete = (vis_long == rel.memory_events.get(row["memory_id"], set())
                and vis_curr == rel.canonical_events.get(row["canonical_id"], set()))
    f.component(complete)
    if not complete:
        f.add("E0_INPUT_TRUNCATED", "payload does not carry the full registered record set",
              "L1.1.9", {"delivered_longitudinal": len(vis_long), "delivered_current": len(vis_curr)})

    # output truncation
    finish = raw.get("finish_reason")
    f.component(finish not in ("length", "max_tokens"))
    if finish in ("length", "max_tokens"):
        f.add("E0_OUTPUT_TRUNCATED", f"provider terminated on a length boundary ({finish})", "L1.1.10")

    # frozen-version agreement
    pinned = contract["record_integrity_checks"][-1]["pinned"]
    ver_ok = run.manifest.get("benchmark_version") == pinned["benchmark_version"]
    f.component(ver_ok)
    if not ver_ok:
        f.add("E0_VERSION_MISMATCH", "run benchmark version differs from the frozen release",
              "L1.1.11", {"run": run.manifest.get("benchmark_version"),
                          "frozen": pinned["benchmark_version"]})

    # ---------------------------------------------------------- 6.2 schema
    can = canonicalise_response(parsed_rec.get("parsed"))
    f.component(bool(can.get("parseable")))
    if not can.get("parseable"):
        f.add("E0_SCHEMA_INVALID", "response is not a parseable JSON object", "L1.2.1",
              {"terminal_status": term.get("terminal_status")})
        return f

    schema_msgs = []
    for k in ("reaction", "rule_id", "decisive_event_ids", "reason"):
        if can.get(k) in (None, []):
            schema_msgs.append(f"missing or empty required field {k}")
    if can["reaction"] not in rel.reaction_enum:
        schema_msgs.append(f"reaction {can['reaction']!r} not in the public vocabulary")
    if can["rule_id"] not in rel.rule_enum:
        schema_msgs.append(f"rule {can['rule_id']!r} not in the public rules")
    if can["undeclared_citations"]:
        schema_msgs.append("cited-event list contains an undeclared identifier form")
    if can["duplicate_citations"]:
        schema_msgs.append("duplicate citation after canonicalisation")
    if can["reason_length_raw"] is None or not (1 <= can["reason_length_raw"] <= 600):
        schema_msgs.append(f"reason length {can['reason_length_raw']} outside 1..600")
    if can["extra_fields"]:
        schema_msgs.append(f"prohibited additional field(s) {can['extra_fields']}")
    f.component(not schema_msgs)
    if schema_msgs:
        f.add("E0_SCHEMA_INVALID", "; ".join(schema_msgs), "L1.2", {"detail": schema_msgs})

    reaction, rule = can["reaction"], can["rule_id"]
    cited = set(can["decisive_event_ids"] or [])

    # ---------------------------------------------------------- 6.3 rule/outcome
    compat = contract["rule_outcome_compatibility"]
    if rule in compat:
        ok = reaction in compat[rule]
        f.component(ok)
        if not ok:
            f.add("E4_RULE_OUTCOME_INCONSISTENT",
                  f"stated rule {rule} cannot produce stated outcome {reaction}", "L1.3",
                  {"rule": rule, "reaction": reaction, "admits": compat[rule]})
            if (reaction == "ESCALATE_REVIEW" and rule in DEFERRAL_RULES) or \
               (reaction == "WAIT_FOR_EVIDENCE" and rule == "R01_REVIEW_BOUNDARY"):
                f.add("E4_REVIEW_DEFER_CONFLATED", "review and deferral conflated", "L1.3.1")
            if (reaction == "WITHHOLD_ASSUMPTION" and rule in DEFERRAL_RULES) or \
               (reaction == "WAIT_FOR_EVIDENCE" and rule in WITHHOLD_RULES):
                f.add("E4_NO_USE_UNRESOLVED_CONFLATED", "withholding and unresolvedness conflated",
                      "L1.3.2")

    # ---------------------------------------------------------- 6.4 citations
    nonexistent = sorted(e for e in cited if e not in rel.events)
    invisible = sorted(e for e in cited if e in rel.events and e not in visible)
    f.component(not nonexistent and not invisible)
    if nonexistent:
        f.add("E1_CITATION_NONEXISTENT", "cited event does not exist in the source-event registry",
              "L1.4.1", {"events": nonexistent})
    if invisible:
        f.add("E1_CITATION_NOT_VISIBLE", "cited event exists but was not delivered in this condition",
              "L1.4.3", {"events": invisible})
    foreign = sorted(e for e in cited
                     if e in rel.events and e not in visible
                     and rel.owner_memory(e) != row["memory_id"])
    if foreign:
        f.add("E1_CITATION_NONEXISTENT", "cited event belongs to a different memory", "L1.4.2",
              {"events": foreign})
    if boundary:
        late = sorted(e for e in cited if e in rel.events
                      and rel.events[e]["event_time"] > boundary)
        f.component(not late)
        if late:
            f.add("E1_TEMPORAL_ORDER_INVALID", "cited event postdates the decision boundary",
                  "L1.4.4", {"events": late, "decision_boundary": boundary})

    # stated source agreement, checked only where the reason places a source token
    # in the immediate window of an event identifier it names
    reason = can["reason"] or ""
    mis_src = []
    for m in EVT_IN_TEXT.finditer(reason):
        eid = m.group(0)
        if eid not in rel.events:
            continue
        window = _clause_around(reason, m.start(), m.end())
        named = [s for s in SOURCE_TOKENS if s in window or s.replace("_", " ") in window]
        if len(named) == 1 and named[0] != rel.events[eid]["source"]:
            mis_src.append({"event": eid, "stated": named[0],
                            "registry": rel.events[eid]["source"]})
    f.component(not mis_src)
    if mis_src:
        f.add("E2_SOURCE_MISATTRIBUTION", "stated source disagrees with the source-event registry",
              "L1.4.6", {"cases": mis_src[:5]})

    # ---------------------------------------------------------- 6.5 grounds
    if reaction in CURRENT_USE_REACTIONS:
        ok = bool(cited & vis_curr)
        f.component(ok)
        if not ok:
            f.add("E1_CURRENT_GROUNDS_MISSING",
                  "current applicability asserted with no cited current record", "L1.5.1",
                  {"reaction": reaction, "cited": sorted(cited)})
    if rule in HISTORICAL_RULES:
        ok = bool(cited & vis_long)
        f.component(ok)
        if not ok:
            f.add("E1_HISTORICAL_GROUNDS_MISSING",
                  "historical relation asserted with no cited longitudinal record", "L1.5.2",
                  {"rule": rule, "cited": sorted(cited)})
    named_any = bool(EVT_IN_TEXT.search(reason))
    f.component(named_any)
    if not named_any:
        f.add("E4_INFLUENCE_UNEXPLAINED",
              "stated reason names no event identifier, so the stated influence cannot be "
              "reconstructed from the reason alone", "L1.5.3")

    # ---------------------------------------------------------- 6.7 scope
    pat = contract["scope_review"]["automated"]["pattern"]
    hit = re.search(pat, reason, re.I)
    f.component(hit is None)
    if hit:
        f.add("E2_SCOPE_OVERREACH", "unsupported clinical or causal assertion in the stated reason",
              "L1.7.1", {"match": hit.group(0)})

    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    rel, run, ont = Release(Path(a.release)), Run(Path(a.run)), Ontology()
    contract = read_json(PKG / "contracts/level1_io_contract.json")
    work = Path(a.work)
    rows = [json.loads(l) for l in open(work / "audit_manifest.jsonl")]
    n = 0
    with open(work / "level1_errors.jsonl", "w") as fh:
        for row in rows:
            for e in audit_case(rel, run, row, ont, contract).errors:
                fh.write(json.dumps(e) + "\n")
                n += 1
    print(json.dumps({"cases": len(rows), "level1_errors": n}, indent=2))


if __name__ == "__main__":
    main()
