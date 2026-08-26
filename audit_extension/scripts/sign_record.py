#!/usr/bin/env python3
"""Stamp a signature onto a governance record, honestly.

    python3 sign_record.py --record validation/FREEZE_audit_extension_2026-08-22.json \
        --mode DELEGATED --signed-by "Adrian Lendinez Ibanez" \
        --on-behalf-of "Renxi Qiu" --instruction "<how the instruction was given>"

Two rules this script enforces, because an audit trail that cannot be trusted is
worse than no audit trail:

  1. A delegated signature is recorded as DELEGATED. `signed_by` always names the
     person who actually typed it. `on_behalf_of` names whoever instructed them.
     The script refuses to write a person's name into `signed_by` on someone
     else's behalf.
  2. Every reader of the record is told the mode. The gate prints it too, so a
     delegated signature can never be mistaken for a direct one further down the
     line.
"""
from __future__ import annotations
import argparse, datetime, json, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--mode", required=True, choices=["DIRECT", "DELEGATED"])
    ap.add_argument("--signed-by", required=True,
                    help="the person who actually signs, always")
    ap.add_argument("--on-behalf-of", help="required for DELEGATED")
    ap.add_argument("--instruction", help="how the delegating instruction was given")
    ap.add_argument("--runs", nargs="*", default=None,
                    help="for an authorisation record: the runs being authorised")
    a = ap.parse_args()

    p = Path(a.record)
    rec = json.loads(p.read_text())

    if a.mode == "DELEGATED":
        if not a.on_behalf_of:
            sys.exit("DELEGATED needs --on-behalf-of")
        if not a.instruction:
            sys.exit("DELEGATED needs --instruction: the trail must say how it was given")
        if a.signed_by.strip().lower() == a.on_behalf_of.strip().lower():
            sys.exit("delegated to and from the same person is not a delegation")
    else:
        if a.on_behalf_of:
            sys.exit("DIRECT takes no --on-behalf-of. If someone else instructed it, "
                     "it is DELEGATED.")

    required = rec.get("signature_required_from")
    satisfies = (a.mode == "DIRECT"
                 and required and a.signed_by.strip().lower() == required.strip().lower())

    rec["signature_status"] = "SIGNED"
    rec["signature_mode"] = a.mode
    rec["signed_by"] = a.signed_by
    rec["signed_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if a.mode == "DELEGATED":
        rec["on_behalf_of"] = a.on_behalf_of
        rec["delegating_instruction"] = a.instruction
        rec["satisfies_signature_requirement_literally"] = bool(satisfies)
        if required and not satisfies:
            rec["signature_caveat"] = (
                f"The record requires the signature of {required}. This is a DELEGATED signature "
                f"by {a.signed_by} on their instruction, not a signature by {required}. Anyone "
                f"relying on this record should know which of the two it is.")
    if a.runs is not None:
        rec["runs_authorised"] = list(a.runs)

    p.write_text(json.dumps(rec, indent=2))
    print(json.dumps({k: rec.get(k) for k in
                      ("record_id", "signature_status", "signature_mode", "signed_by",
                       "on_behalf_of", "signed_at", "runs_authorised",
                       "satisfies_signature_requirement_literally")}, indent=2))


if __name__ == "__main__":
    main()
