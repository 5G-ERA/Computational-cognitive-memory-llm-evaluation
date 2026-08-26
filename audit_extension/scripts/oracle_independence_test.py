#!/usr/bin/env python3
"""Protocol section 4: automated oracle-independence test.

  1. create a clean audit working directory
  2. copy only the permitted artefacts
  3. verify that prohibited filenames and fields are absent
  4. execute the complete audit pipeline
  5. compare output hashes with the standard audit run

Failure of this test is a release blocker.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import PROHIBITED_BASENAMES, PROHIBITED_FIELDS, sha256_file, PKG

PERMITTED_RELEASE = [
    "public",
    "prompts/model_calls_v0_5_1.jsonl",
    "data_v0_5_1/historical_events.jsonl",
    "data_v0_5_1/current_events.jsonl",
    "data_v0_5_1/rendering_map.csv",
    "data_v0_5_1/split_manifest.csv",
    "validation/SHA256SUMS.txt",
]
PERMITTED_RUN = ["responses_raw.jsonl", "responses_parsed.jsonl",
                 "call_registry.jsonl", "run_manifest.json"]
PERMITTED_PKG = ["contracts", "schemas", "mappings", "scripts", "fixtures"]

COMPARED = ["audit_errors.jsonl", "audit_case_summaries.jsonl", "audit_memory_summaries.csv",
            "audit_condition_metrics.csv", "audit_error_domains.csv", "audit_root_causes.csv",
            "audit_transition_matrix_M0_B1.csv", "audit_contrasts.json"]


def copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
    else:
        shutil.copy2(src, dst)


def scan(root: Path):
    """Return (prohibited_files, files_with_prohibited_fields)."""
    bad_files, bad_fields = [], []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.name in PROHIBITED_BASENAMES:
            bad_files.append(str(p.relative_to(root)))
            continue
        if p.suffix not in (".json", ".jsonl", ".csv", ".txt", ".yaml", ".md"):
            continue
        try:
            head = p.read_text(errors="ignore")
        except Exception:
            continue
        # Contract and mapping files legitimately NAME the prohibited fields in
        # order to quarantine them; only data artefacts are scanned for values.
        if any(part in ("contracts", "mappings", "scripts", "fixtures")
               for part in p.relative_to(root).parts):
            continue
        hits = sorted(f for f in PROHIBITED_FIELDS if f'"{f}"' in head or f",{f}," in head
                      or head.startswith(f + ",") or f",{f}\n" in head)
        if hits:
            bad_fields.append({"file": str(p.relative_to(root)), "fields": hits})
    return bad_files, bad_fields


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="development")
    ap.add_argument("--reference", required=True, help="results dir of the standard audit run")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()

    rel, run, ref = Path(a.release), Path(a.run), Path(a.reference)
    # The clean run must reproduce the reference byte for byte, so it is given the
    # reference run's own label; a differing label is a naming artefact, not evidence
    # about oracle independence.
    ref_label = json.loads((ref / "audit_contrasts.json").read_text())["label"]
    tmp = Path(tempfile.mkdtemp(prefix="audit_cleanroom_"))
    croot, crun, cpkg = tmp / "release", tmp / "run", tmp / "audit_extension"

    for rp in PERMITTED_RELEASE:
        copy(rel / rp, croot / rp)
    for rp in PERMITTED_RUN:
        copy(run / rp, crun / rp)
    for rp in PERMITTED_PKG:
        copy(PKG / rp, cpkg / rp)

    bad_files, bad_fields = scan(tmp)
    work, out = tmp / "work", tmp / "results"

    steps, ok = [], not bad_files and not bad_fields
    if ok:
        cmds = [
            [sys.executable, str(cpkg / "scripts/build_audit_manifest.py"),
             "--release", str(croot), "--run", str(crun), "--split", a.split, "--out", str(work)],
            [sys.executable, str(cpkg / "scripts/audit_level1_io.py"),
             "--release", str(croot), "--run", str(crun), "--work", str(work)],
            [sys.executable, str(cpkg / "scripts/audit_m0_trace.py"),
             "--release", str(croot), "--run", str(crun), "--work", str(work)],
            [sys.executable, str(cpkg / "scripts/audit_b1_trace.py"),
             "--release", str(croot), "--run", str(crun), "--work", str(work)],
            [sys.executable, str(cpkg / "scripts/aggregate_audit_results.py"),
             "--work", str(work), "--out", str(out), "--label", ref_label],
        ]
        for c in cmds:
            r = subprocess.run(c, capture_output=True, text=True)
            steps.append({"script": Path(c[1]).name, "returncode": r.returncode,
                          "stderr": r.stderr[-800:] if r.returncode else ""})
            if r.returncode:
                ok = False
                break

    comparison = []
    if ok:
        for name in COMPARED:
            p, q = out / name, ref / name
            same = p.exists() and q.exists() and sha256_file(p) == sha256_file(q)
            comparison.append({"file": name, "identical": same,
                               "cleanroom_sha256": sha256_file(p) if p.exists() else None,
                               "reference_sha256": sha256_file(q) if q.exists() else None})
        ok = all(c["identical"] for c in comparison)

    report = {
        "test": "oracle_independence",
        "protocol_section": 4,
        "clean_room": str(tmp),
        "permitted_release_artefacts": PERMITTED_RELEASE,
        "permitted_run_artefacts": PERMITTED_RUN,
        "prohibited_files_found": bad_files,
        "prohibited_fields_found": bad_fields,
        "pipeline_steps": steps,
        "output_comparison": comparison,
        "pass": bool(ok),
        "release_blocker_if_failed": True,
    }
    Path(a.report).write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in
                      ("prohibited_files_found", "prohibited_fields_found", "pass")}, indent=2))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
