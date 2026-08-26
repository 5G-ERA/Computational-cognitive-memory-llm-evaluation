#!/usr/bin/env python3
"""Run the whole audit extension end to end for one executed split.

  python3 run_audit.py --release <release_root> --run <run_dir> \
      --split development --label dev_terra --out <results_dir>

Runs each protocol-mandated script in order, then the section 14
reproducibility checks and the section 12 report.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def step(cmd):
    print("\n$ " + " ".join(Path(c).name if c.endswith(".py") else c for c in cmd[1:]))
    r = subprocess.run(cmd, text=True)
    if r.returncode:
        sys.exit(f"step failed: {cmd[1]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="development")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    work = out / "work"
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    py = sys.executable

    step([py, str(HERE / "build_audit_manifest.py"), "--release", a.release, "--run", a.run,
          "--split", a.split, "--out", str(work)])
    step([py, str(HERE / "audit_level1_io.py"), "--release", a.release, "--run", a.run,
          "--work", str(work)])
    step([py, str(HERE / "audit_m0_trace.py"), "--release", a.release, "--run", a.run,
          "--work", str(work)])
    step([py, str(HERE / "audit_b1_trace.py"), "--release", a.release, "--run", a.run,
          "--work", str(work)])
    step([py, str(HERE / "aggregate_audit_results.py"), "--work", str(work), "--out", str(out),
          "--label", a.label])
    step([py, str(HERE / "reproducibility_checks.py"), "--release", a.release, "--run", a.run,
          "--split", a.split, "--out", str(out / "reproducibility_report.json")])
    step([py, str(HERE / "generate_audit_report.py"), "--results", str(out), "--label", a.label,
          "--repro", str(out / "reproducibility_report.json"),
          "--out", str(out / "audit_report.md")])
    print("\ndone ->", out)


if __name__ == "__main__":
    main()
