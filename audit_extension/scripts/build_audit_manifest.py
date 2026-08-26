#!/usr/bin/env python3
"""Protocol section 5: one JSONL manifest row per expected call.

    python3 build_audit_manifest.py --release <release_root> --run <run_dir> \
        --split development --out <workdir>

Validation performed here, before any audit runs:
  - exactly one row per expected call, zero duplicate call IDs
  - manifest count equals the frozen call registry count for the split
The manifest carries the payload hash, so every later record-integrity check
compares against a value fixed at manifest time.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Release, Run, read_json, sha256_obj, PKG


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="development", choices=["development", "reserved"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rel, run = Release(Path(a.release)), Run(Path(a.run))
    # Contract identifiers are read from the contracts, never restated here, so a
    # contract revision cannot silently disagree with the manifest that cites it.
    cid = {k: read_json(PKG / f"contracts/{v}")["contract_id"] for k, v in
           (("L1", "level1_io_contract.json"), ("M0", "m0_prospective_contract.json"),
            ("B1", "b1_resolved_contract.json"))}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    expected = [c for c in rel.calls.values() if rel.split[c["memory_id"]] == a.split]
    rows, seen = [], set()
    for c in sorted(expected, key=lambda x: x["call_id"]):
        if c["call_id"] in seen:
            sys.exit(f"MANIFEST: duplicate call id {c['call_id']}")
        seen.add(c["call_id"])
        ctx = rel.context_map[c["context_id"]]
        cond = c["condition"]
        rows.append({
            "call_id": c["call_id"],
            "memory_id": c["memory_id"],
            "context_id": c["context_id"],
            "canonical_id": c["canonical_id"],
            "condition": cond,
            "rendering": ctx["rendering"],
            "payload_path": "prompts/model_calls_v0_5_1.jsonl#" + c["call_id"],
            "payload_sha256": sha256_obj(c["payload"]),
            "raw_response_path": "responses_raw.jsonl#" + c["call_id"],
            "terminal_record_path": "call_registry.jsonl#" + c["call_id"],
            "parsed_response_path": "responses_parsed.jsonl#" + c["call_id"],
            "event_registry_path": "event_registry.json",
            "m0_trace_path": ("payload#open_loop_memory"
                              if cond == "M0_OPEN_LOOP_MEMORY" else None),
            "b1_trace_path": ("payload#verified_cognitive_memory"
                              if cond == "B1_VERIFIED_MEMORY" else None),
            "level1_contract": cid["L1"],
            "level2_contract": {"B0_LLM_ALONE": None,
                                "M0_OPEN_LOOP_MEMORY": cid["M0"],
                                "B1_VERIFIED_MEMORY": cid["B1"]}[cond],
        })

    with open(out / "audit_manifest.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    # Oracle-free projections the clean room is allowed to receive.
    (out / "context_map.oracle_free.json").write_text(
        json.dumps(rel.context_map, indent=1, sort_keys=True))
    (out / "event_registry.json").write_text(
        json.dumps(rel.events, indent=1, sort_keys=True))

    registry_count = len(run.terminal)
    report = {
        "split": a.split,
        "expected_calls": len(rows),
        "unique_call_ids": len(seen),
        "frozen_call_registry_count": registry_count,
        "counts_agree": len(rows) == registry_count,
        "conditions": {c: sum(1 for r in rows if r["condition"] == c)
                       for c in sorted({r["condition"] for r in rows})},
        "renderings": {c: sum(1 for r in rows if r["rendering"] == c)
                       for c in sorted({r["rendering"] for r in rows})},
        "memories": len({r["memory_id"] for r in rows}),
    }
    (out / "manifest_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not report["counts_agree"]:
        sys.exit("MANIFEST: expected-call count does not equal the frozen call registry count")


if __name__ == "__main__":
    main()
