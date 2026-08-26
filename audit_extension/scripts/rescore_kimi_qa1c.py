#!/usr/bin/env python3
"""Re-score the Kimi reserved run under the frozen qa1c parser, for the pre-registered test.

The Kimi reserved decision result (FASE 17, +9.79 pp) was computed by re-parsing
responses_raw.jsonl with the qa1c parser, which tolerates the `◁/think` marker
Kimi emits without its closing glyph. The qa1b scoring_records.jsonl in the run
directory predates that fix and marks 93 responses truncated instead of 58.

A confirmatory test must use the same parse as the frozen decision result, and
that choice must be fixed BEFORE the pre-registration is signed. This script
produces that input and prints counts only. It computes NOTHING about rendering
agreement: no replay quantity is touched.

Oracle: read, to attach rule_correct. Kimi's oracle was unsealed on 16 August.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--package", required=True, help="the qa1c release root")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run, pkg = Path(a.run), Path(a.package)

    sys.path.insert(0, str(pkg / "scripts"))
    from qa_core import parse_final_answer            # noqa: E402  frozen qa1c parser
    from core import schema_errors, interpret         # noqa: E402

    raw = {}
    for line in (run / "responses_raw.jsonl").open():
        r = json.loads(line); raw.setdefault(r["call_id"], r)
    refs = {x["context_id"]: x for x in
            (json.loads(l) for l in (pkg / "hidden/oracle_references_v0_5_1.jsonl").open())}
    split = {x["memory_id"]: x["split"].lower()
             for x in csv.DictReader((pkg / "data_v0_5_1/split_manifest.csv").open())}

    n = 0; status = {}; by_cond = {}
    with open(a.out, "w") as fh:
        for line in (pkg / "prompts/model_calls_v0_5_1.jsonl").open():
            c = json.loads(line)
            if split[c["memory_id"]] != "reserved":
                continue
            rec = {"call_id": c["call_id"], "memory_id": c["memory_id"],
                   "context_id": c["context_id"], "canonical_id": c["canonical_id"],
                   "condition": c["condition"], "status": "MISSING", "parsed": None,
                   "reaction_correct": False, "rule_correct": False,
                   "parser": "qa1c"}
            r = raw.get(c["call_id"])
            if r is not None:
                pr = parse_final_answer(r.get("assistant_text") or "", None,
                                        finish_reason=r.get("finish_reason"))
                rec["status"] = pr.status
                if pr.status == "COMPLETED_VALID" and isinstance(pr.obj, dict):
                    if schema_errors(pr.obj):
                        rec["status"] = "COMPLETED_INVALID_SCHEMA"
                    else:
                        legacy = interpret(pr.obj, c["payload"], refs[c["context_id"]], c["condition"])
                        rec["parsed"] = {"reaction": pr.obj.get("reaction"),
                                         "rule_id": pr.obj.get("rule_id"),
                                         "decisive_event_ids": pr.obj.get("decisive_event_ids")}
                        rec["reaction_correct"] = bool(legacy["reaction_correct"]) and bool(legacy.get("reaction_rule_consistent"))
                        rec["rule_correct"] = bool(legacy["rule_correct"])
            fh.write(json.dumps(rec) + "\n"); n += 1
            status[rec["status"]] = status.get(rec["status"], 0) + 1
            if rec["status"] == "COMPLETED_VALID":
                by_cond[rec["condition"]] = by_cond.get(rec["condition"], 0) + 1

    h = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()
    print(json.dumps({"records": n, "status": status, "valid_by_condition": by_cond,
                      "sha256": h}, indent=2))


if __name__ == "__main__":
    main()
