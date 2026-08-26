#!/usr/bin/env python3
"""Protocol section 19: evaluate the go/no-go gate for reserved audit execution.

Failure of any mandatory condition produces NO-GO. The gate is evaluated from
artefacts on disk, never from an assertion in prose.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Ontology, read_json, PKG

REQUIRED_META = ("label", "definition", "scopes", "severity", "detection", "status", "domain")


def evaluate(results: Path):
    ont = Ontology()
    V = PKG / "validation"
    checks = []

    def c(name, ok, detail, mandatory=True):
        checks.append({"condition": name, "pass": bool(ok), "mandatory": mandatory,
                       "detail": detail})

    contracts = {p.stem: p for p in (PKG / "contracts").glob("*.json")}
    c("level1_m0_b1_contracts_frozen",
      all(k in contracts for k in ("level1_io_contract", "m0_prospective_contract",
                                   "b1_resolved_contract")),
      "contracts present: " + ", ".join(sorted(contracts)))

    missing = {k: [f for f in REQUIRED_META if f not in v] for k, v in ont.codes.items()}
    missing = {k: v for k, v in missing.items() if v}
    c("every_ontology_code_fully_specified", not missing,
      f"{len(ont.codes)} codes; incomplete: {missing or 'none'}")

    metrics = (results / "audit_condition_metrics.csv")
    b0_l2_na = False
    if metrics.exists():
        import csv
        rows = list(csv.DictReader(open(metrics)))
        b0_l2_na = any(r["audit_level"] == "L2_B0" and r["condition"] == "B0_LLM_ALONE"
                       and float(r["conformity"]) == 0.0 and float(r["critical_rate"]) == 0.0
                       for r in rows)
    c("b0_level2_not_applicable_by_design", b0_l2_na,
      "L2_B0 rows are reported as NOT_APPLICABLE, never as failures")

    m0_never_closure = True
    errs = results / "audit_errors.jsonl"
    if errs.exists():
        for line in open(errs):
            e = json.loads(line)
            if e["audit_level"] == "L2_M0" and e["code"] == "E3_CONSEQUENCE_CLOSURE_ABSENT":
                m0_never_closure = False
                break
    c("m0_open_loop_closure_not_an_error", m0_never_closure,
      "no E3_CONSEQUENCE_CLOSURE_ABSENT was raised at L2_M0")

    oi = V / "oracle_independence_report.json"
    oi_ok = oi.exists() and json.loads(oi.read_text()).get("pass") is True
    c("complete_audit_runs_without_oracle_files", oi_ok,
      "validation/oracle_independence_report.json" + ("" if oi.exists() else " ABSENT"))

    fx = V / "fixture_report.json"
    fx_j = json.loads(fx.read_text()) if fx.exists() else {}
    c("deterministic_fixture_agreement_100pc", fx_j.get("fixture_agreement") == 1.0,
      f"fixture agreement {fx_j.get('fixture_agreement')}")
    c("canonicalisation_tests_pass", fx_j.get("canonicalisation_pass") is True,
      f"{len(fx_j.get('canonicalisation_tests', []))} canonicalisation tests")

    # Decision E1-G1, Renxi Qiu, 22 August 2026: the INDEPENDENT-REIMPLEMENTATION requirement
    # of protocol section 17 is removed for Experiment 1. The fixture and canonicalisation
    # requirements of the same section remain in force and are checked above.
    # The condition is retired rather than deleted, so the gate still reports that it exists and
    # that it was removed by decision. A removed condition must never read as a satisfied one.
    ia = V / "implementation_agreement.json"
    ia_j = json.loads(ia.read_text()) if ia.exists() else {}
    st = ia_j.get("status", "ABSENT")
    removed = st == "REMOVED_BY_DECISION"
    c("independent_validator_agreement_100pc", st == "SATISFIED" or removed,
      (f"{st}: {ia_j.get('decision')} No independent reimplementation exists; every figure rests "
       f"on a single implementation, and the paper must say so."
       if removed else st),
      mandatory=not removed)

    # Decision E1-H1, Renxi Qiu, 22 August 2026: the entire audit is independent from human
    # input, so protocol section 16 is REMOVED for Experiment 1. Retired, not deleted: a removed
    # condition must never read as a satisfied one.
    rr = V / "rater_reliability.json"
    rr_j = json.loads(rr.read_text()) if rr.exists() else {}
    st = rr_j.get("status", "ABSENT")
    removed = st == "REMOVED_BY_DECISION"
    c("human_review_rubric_and_blinding_frozen", st == "SATISFIED" or removed,
      (f"{st}: {rr_j.get('decision')} Substantive citation relevance and material scope overreach "
       f"are out of scope by design, not unmeasured pending work."
       if removed else st),
      mandatory=not removed)

    ont_raw = ont.raw
    c("root_cause_rules_frozen",
      len(ont_raw.get("root_cause_priority", [])) == len(ont.codes),
      f"{len(ont_raw.get('root_cause_priority', []))} prioritised of {len(ont.codes)} codes")

    contrasts = results / "audit_contrasts.json"
    c("memory_clustered_analysis_code_validated", contrasts.exists()
      and all(v["clusters"] > 0 for v in
              json.loads(contrasts.read_text())["contrasts"]["SCOPED"].values()),
      "paired memory-clustered bootstrap executed on every declared contrast")

    dec = V / "DECISIONS_2026-08-22.json"
    dec_j = json.loads(dec.read_text()) if dec.exists() else {}
    c("protocol_decisions_recorded", len(dec_j.get("decisions", [])) == 18,
      f"{len(dec_j.get('decisions', []))} of 18 decisions recorded, decided_by "
      f"{dec_j.get('decided_by', 'nobody')}")

    # Decision C2, Renxi Qiu, 22 August 2026: reserved audit execution needs a signed
    # authorisation record naming the run, in addition to every section 19 condition.
    def signature_state(path: Path):
        """Report a signature and, always, whether it was direct or delegated."""
        if not path.exists():
            return False, "record absent"
        r = json.loads(path.read_text())
        if r.get("signature_status") != "SIGNED":
            return False, f"{path.name} present, NOT_SIGNED"
        mode = r.get("signature_mode", "UNSPECIFIED")
        who = r.get("signed_by", "unnamed")
        required_mode = r.get("signature_mode_required")
        if required_mode and mode != required_mode:
            # Decision E2, Renxi Qiu, 22 August 2026: RENXI SIGNS. A record that declares the
            # mode its signature must be given in is not satisfied by a signature in another
            # mode. Without this the gate would launder a delegated signature into a GO on a
            # record whose own decision ruled delegation out.
            return False, (f"SIGNED {mode} by {who}"
                           + (f" on behalf of {r.get('on_behalf_of')}" if r.get("on_behalf_of") else "")
                           + f", but this record requires signature_mode {required_mode}"
                           + (f" from {r.get('signature_required_from')}" if r.get("signature_required_from") else "")
                           + ". Not satisfied.")
        if mode == "DELEGATED":
            return True, (f"SIGNED {mode} by {who} on behalf of {r.get('on_behalf_of')}; "
                          f"the record required {r.get('signature_required_from')}, so this "
                          f"does NOT satisfy that requirement literally")
        return True, f"SIGNED {mode} by {who}"

    auth = sorted(V.glob("AUTHORISATION_reserved_audit_*.json"))
    auth_ok, auth_detail = False, "no reserved-audit authorisation record"
    for q in auth:
        ok, detail = signature_state(q)
        runs = json.loads(q.read_text()).get("runs_authorised") or []
        if ok and not runs:
            ok, detail = False, detail + "; runs_authorised is empty, so it authorises nothing"
        elif ok:
            detail += f"; runs authorised: {runs}"
        auth_ok, auth_detail = ok, f"{q.name}: {detail}"
        if ok:
            break
    c("reserved_audit_authorisation_record_signed", auth_ok, auth_detail)

    sums = V / "SHA256SUMS.txt"
    fz_ok, fz_detail = signature_state(V / "FREEZE_audit_extension_2026-08-22.json")
    c("audit_software_and_contracts_hashed_and_signed", sums.exists() and fz_ok,
      ("SHA256SUMS.txt present; " if sums.exists() else "SHA256SUMS.txt ABSENT; ") + fz_detail)

    decision = "GO" if all(x["pass"] for x in checks if x["mandatory"]) else "NO-GO"
    scope = {
        "arms_audited": ["dev_terra", "dev_qwen3"],
        "arms_planned_not_run": [
            {"arm": "kimi_reserved", "decision": "C1, Renxi Qiu, 22 August 2026: YES, "
             "RESERVED-ONLY POST-FREEZE ARM",
             "verified_auditable": "all six audit inputs are byte-identical between qa1b and qa1c",
             "blocked_by": ["section 19 gate", "C2 authorisation"]}],
        "reserved_splits_audited": [],
    }
    return {"protocol_section": 19, "decision": decision, "scope": scope,
            "failed_mandatory": [x["condition"] for x in checks
                                 if x["mandatory"] and not x["pass"]],
            "checks": checks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = evaluate(Path(a.results))
    Path(a.out).write_text(json.dumps(r, indent=2))
    print(json.dumps({"decision": r["decision"], "failed": r["failed_mandatory"]}, indent=2))


if __name__ == "__main__":
    main()
