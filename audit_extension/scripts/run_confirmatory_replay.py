#!/usr/bin/env python3
"""The pre-registered confirmatory test of replay recall, and nothing else.

Refuses to run on the confirmatory arm unless:
  1. the pre-registration record is SIGNED
  2. the reserved-audit authorisation for the arm is SIGNED
  3. the input file's sha256 matches the one pinned in the pre-registration
  4. no confirmatory result file already exists (one shot)

Computes exactly the endpoints the record names, with the code hash the record
pins, and seals the output with the hashes of everything it read.

--dry-run-on <scored.jsonl> runs the identical computation on an arm that is
already open (Qwen3 reserved), to show the machinery reproduces the exploratory
number. A dry run never touches the confirmatory input.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calculate_clustered_intervals import paired_difference, paired_permutation

PKG = Path(__file__).resolve().parents[1]
CONDS = ("B0_LLM_ALONE", "M0_OPEN_LOOP_MEMORY", "B1_VERIFIED_MEMORY")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(path: Path):
    rec = {}
    for l in open(path):
        r = json.loads(l)
        if r.get("status") == "COMPLETED_VALID" and isinstance(r.get("parsed"), dict):
            rec[r["call_id"]] = dict(cond=r["condition"], mem=r["memory_id"], canon=r["canonical_id"],
                                     rend=r["context_id"][-3:], rule=r["parsed"]["rule_id"],
                                     cites=frozenset(r["parsed"].get("decisive_event_ids") or []),
                                     ok=bool(r["rule_correct"]),
                                     rok=bool(r.get("reaction_correct")))
    return rec


def groups(rec, cond):
    g = collections.defaultdict(dict)
    for v in rec.values():
        if v["cond"] == cond:
            g[(v["mem"], v["canon"])][v["rend"]] = v
    full = {k: v for k, v in g.items() if len(v) == 3}
    return full, sum(1 for v in g.values() if len(v) < 3)


def endpoints(rec):
    out = {"by_condition": {}, "dropped_incomplete": {}}
    pm_recall, pm_consist, pm_stab_ok, pm_stab_err = {}, {}, {}, {}
    for cond in CONDS:
        full, dropped = groups(rec, cond)
        out["dropped_incomplete"][cond] = dropped
        R = collections.defaultdict(lambda: [0, 0]); C = collections.defaultdict(lambda: [0, 0])
        S_ok = collections.defaultdict(lambda: [0, 0]); S_err = collections.defaultdict(lambda: [0, 0])
        for (mem, _), v in full.items():
            rules = {x["rule"] for x in v.values()}
            err = any(not x["ok"] for x in v.values())
            flag = len(rules) > 1
            C[mem][1] += 1; C[mem][0] += int(not flag)
            if err:
                R[mem][1] += 1; R[mem][0] += int(flag)
            stable = len({x["cites"] for x in v.values()}) == 1
            tgt = S_err if any(not x["rok"] for x in v.values()) else S_ok
            tgt[mem][1] += 1; tgt[mem][0] += int(stable)
        pm_recall[cond] = {m: tuple(x) for m, x in R.items()}
        pm_consist[cond] = {m: tuple(x) for m, x in C.items()}
        pm_stab_ok[cond] = {m: tuple(x) for m, x in S_ok.items()}
        pm_stab_err[cond] = {m: tuple(x) for m, x in S_err.items()}
        rate = lambda pm: (100.0 * sum(v[0] for v in pm.values()) / sum(v[1] for v in pm.values())) if pm and sum(v[1] for v in pm.values()) else None
        out["by_condition"][cond] = {
            "boundaries": len(full),
            "recall": rate(pm_recall[cond]), "erroneous_boundaries": sum(v[1] for v in pm_recall[cond].values()),
            "rule_consistency": rate(pm_consist[cond]),
            "citation_stability_all_correct": rate(pm_stab_ok[cond]),
            "citation_stability_with_error": rate(pm_stab_err[cond])}
    mems = sorted({v["mem"] for v in rec.values()})
    def contrast(pm):
        a, b = pm["B1_VERIFIED_MEMORY"], pm["B0_LLM_ALONE"]
        common = [m for m in mems if m in a and m in b]
        return {"difference": paired_difference(a, b, common), "permutation": paired_permutation(a, b, common)}
    out["PRIMARY_recall_B1_minus_B0"] = contrast(pm_recall)
    out["secondary_rule_consistency_B1_minus_B0"] = contrast(pm_consist)
    out["secondary_stability_flip"] = {
        "B0_correct_minus_error": (out["by_condition"]["B0_LLM_ALONE"]["citation_stability_all_correct"] or 0) - (out["by_condition"]["B0_LLM_ALONE"]["citation_stability_with_error"] or 0),
        "B1_correct_minus_error": (out["by_condition"]["B1_VERIFIED_MEMORY"]["citation_stability_all_correct"] or 0) - (out["by_condition"]["B1_VERIFIED_MEMORY"]["citation_stability_with_error"] or 0)}
    d = out["PRIMARY_recall_B1_minus_B0"]["difference"]
    out["success_criterion_met"] = bool(d["point"] > 0 and d["lo"] > 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run-on", help="an already-open scored file; never the confirmatory input")
    ap.add_argument("--out")
    a = ap.parse_args()
    V = PKG / "validation"

    if a.dry_run_on:
        rec = load(Path(a.dry_run_on))
        res = endpoints(rec); res["mode"] = "DRY_RUN"; res["input"] = a.dry_run_on
        Path(a.out or "/dev/stdout").write_text(json.dumps(res, indent=2)) if a.out else None
        d = res["PRIMARY_recall_B1_minus_B0"]["difference"]; p = res["PRIMARY_recall_B1_minus_B0"]["permutation"]
        print(f"DRY RUN on {a.dry_run_on}: recall B1-B0 = {d['point']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}] p={p['p']:.4f} clusters={d['clusters']}")
        return

    prereg_p = V / "PREREG_replay_recall_kimi_2026-08-22.json"
    prereg = json.loads(prereg_p.read_text())
    auth_p = V / "AUTHORISATION_reserved_audit_002.json"
    auth = json.loads(auth_p.read_text())
    inp = PKG / prereg["confirmatory_sample"]["input_file"]
    out_p = PKG / "results/kimi_confirmatory/CONFIRMATORY_RESULT.json"

    blockers = []
    if prereg.get("signature_status") != "SIGNED":
        blockers.append("pre-registration is NOT_SIGNED")
    if auth.get("signature_status") != "SIGNED":
        blockers.append("AUTHORISATION_reserved_audit_002 is NOT_SIGNED")
    if sha(inp) != prereg["confirmatory_sample"]["input_sha256"]:
        blockers.append("input sha256 does not match the pinned value")
    if out_p.exists():
        blockers.append("a confirmatory result already exists; this test runs once")
    if blockers:
        print("REFUSED:"); [print("  -", b) for b in blockers]; sys.exit(2)

    rec = load(inp)
    res = endpoints(rec)
    res.update({"mode": "CONFIRMATORY", "arm": prereg["confirmatory_sample"]["arm"],
                "prereg_sha256_at_run": sha(prereg_p), "authorisation_sha256_at_run": sha(auth_p),
                "input_sha256": sha(inp),
                "interval_code_sha256": hashlib.sha256((PKG / "scripts/calculate_clustered_intervals.py").read_bytes()).hexdigest(),
                "pinned_interval_code_sha256": prereg["primary_endpoint"]["implementation"].split()[-1]})
    res["code_hash_matches_prereg"] = res["interval_code_sha256"] == res["pinned_interval_code_sha256"]
    out_p.write_text(json.dumps(res, indent=2))
    d = res["PRIMARY_recall_B1_minus_B0"]["difference"]; p = res["PRIMARY_recall_B1_minus_B0"]["permutation"]
    print(f"CONFIRMATORY: recall B1-B0 = {d['point']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}] p={p['p']:.4f} "
          f"clusters={d['clusters']} | success={res['success_criterion_met']} | code hash ok={res['code_hash_matches_prereg']}")


if __name__ == "__main__":
    main()
