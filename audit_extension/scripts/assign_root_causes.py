#!/usr/bin/env python3
"""Protocol section 11: one root cause per case, every code retained.

Case conformity uses every error. Root-cause counts use only the primary code,
so one underlying defect is counted once however many diagnostics it produced.
"""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auditlib import Ontology


def assign(errors, ont: Ontology):
    """Return (root_cause_id, primary_error_code, secondary_error_codes)."""
    if not errors:
        return None, None, []
    codes = sorted({e["code"] for e in errors})
    primary = min(codes, key=lambda c: (ont.rank(c), c))
    secondary = [c for c in codes if c != primary]
    rid = "ROOT-" + hashlib.sha256(
        (errors[0]["call_id"] + "|" + errors[0]["audit_level"] + "|" + primary)
        .encode()).hexdigest()[:8].upper()
    return rid, primary, secondary


if __name__ == "__main__":
    print(__doc__)
