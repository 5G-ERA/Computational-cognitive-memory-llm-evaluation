#!/usr/bin/env python3
"""One-command verification of the Experiment 1 headline results.

Everything runs offline from the frozen records in this repository —
no model calls, no network.

1. Terra and Qwen3 (reserved): re-derives the full result from the raw
   terminal captures through the frozen pipeline (parse -> schema check
   -> scoring -> memory-clustered percentile bootstrap, 10,000
   replicates, seed 13082654) via reproduce/run_frozen_analysis.py, and
   compares accuracies, primary contrast and 95% CI against the frozen
   analysis outputs and results_table_v5_8.json.
2. Kimi arm (reserved): recomputes per-condition accuracy and the
   primary contrast from the qa1c-scored records of the sealed
   confirmatory run and compares them against the signed result.

Requires numpy (for the frozen bootstrap). Exit code 0 = everything
matches.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS = ["B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY"]


def fail(msg):
    print("MISMATCH:", msg)
    return 1


def verify_bedrock_arm(run, arm, frozen_path, expected, tmpdir):
    out = Path(tmpdir) / f"repro_{arm}.json"
    r = subprocess.run(
        [sys.executable, str(ROOT / "reproduce" / "run_frozen_analysis.py"),
         run, arm, str(out)],
        capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        print(r.stdout[-2000:], r.stderr[-2000:])
        return fail(f"{arm}: frozen pipeline did not complete")
    new = json.loads(out.read_text())
    old = json.loads((ROOT / frozen_path).read_text())
    n = 0
    if new["accuracy"] != old["accuracy"]:
        n += fail(f"{arm}: accuracies differ from {frozen_path}")
    if new["primary"] != old["primary"]:
        n += fail(f"{arm}: primary contrast differs from {frozen_path}")
    est, ci = new["primary"]["estimate_pp"], new["primary"]["ci95_pp"]
    want = expected["contrasts_pp"]["CM_minus_Raw"]
    if abs(est - want["estimate"]) >= 5e-4 or [round(x, 4) for x in ci] != [round(x, 4) for x in want["ci95"]]:
        n += fail(f"{arm}: results_table_v5_8.json disagrees")
    print(f"== {arm}: re-derived from raw captures. "
          f"CM-Raw {est:+.4f} pp, CI95 [{ci[0]:.4f}, {ci[1]:.4f}] "
          f"{'OK' if n == 0 else ''}")
    for c in CONDITIONS:
        print(f"   {c:<20} {new['accuracy'][c]:.6f}")
    return n


def verify_kimi(expected):
    scored = ROOT / "audit_extension/results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl"
    correct = {c: 0 for c in CONDITIONS}
    total = {c: 0 for c in CONDITIONS}
    for line in scored.open():
        r = json.loads(line)
        total[r["condition"]] += 1
        if r.get("reaction_correct") is True:
            correct[r["condition"]] += 1
    n = 0
    if set(total.values()) != {480}:
        n += fail(f"kimi: expected 480 calls per condition, got {total}")
    acc = {c: correct[c] / total[c] for c in CONDITIONS}
    delta = (acc["B1_VERIFIED_MEMORY"] - acc["B0_LLM_ALONE"]) * 100
    key = {"B0_LLM_ALONE": "Raw", "M0_OPEN_LOOP_MEMORY": "Map", "B1_VERIFIED_MEMORY": "CM"}
    for c in CONDITIONS:
        if abs(acc[c] - expected["accuracy"][key[c]]) >= 5e-7:
            n += fail(f"kimi: accuracy {c} = {acc[c]:.6f}, table says {expected['accuracy'][key[c]]}")
    want = expected["contrasts_pp"]["CM_minus_Raw"]["estimate"]
    if abs(delta - want) >= 5e-4:
        n += fail(f"kimi: CM-Raw = {delta:+.4f} pp, signed result is {want:+.4f}")
    print(f"== kimi arm (kimi-dev-72b): recomputed from qa1c-scored records. "
          f"CM-Raw {delta:+.4f} pp {'OK' if n == 0 else ''}")
    for c in CONDITIONS:
        print(f"   {c:<20} {acc[c]:.6f}")
    print("   (95% CI [+5.00, +14.79] is the signed confirmatory bootstrap output)")
    return n


def main():
    table = json.loads((ROOT / "results_table_v5_8.json").read_text())
    exp = {m["paper_label"]: m for m in table["models"]}
    failures = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        failures += verify_bedrock_arm("out/reserved_terra", "terra",
                                       "bedrock_terra/out/analysis_reserved_terra.json",
                                       exp["GPT-4.6 Terra"], tmpdir)
        failures += verify_bedrock_arm("out/reserved_qwen3", "qwen3",
                                       "bedrock_terra/out/analysis_reserved_qwen3.json",
                                       exp["Qwen3"], tmpdir)
    failures += verify_kimi(exp["KIMI2"])
    print()
    if failures:
        print(f"{failures} mismatch(es): the repository does NOT reproduce the frozen results.")
        return 1
    print("All three arms reproduce the frozen results, including the")
    print("bootstrap intervals of the Bedrock arms (deterministic seed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
