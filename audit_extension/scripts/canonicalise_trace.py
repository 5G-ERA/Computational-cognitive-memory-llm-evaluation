#!/usr/bin/env python3
"""Canonicalisation for the Experiment 1 audit extension (protocol section 6.2).

Rules, in the order the protocol lists them:
  - trim whitespace
  - normalise permitted identifier case
  - sort identifier sets
  - represent absent optional values as JSON null
  - reject undeclared label aliases
  - retain the original raw value in a side field

Every canonicalising function returns (canonical_value, raw_value) so the raw
value is always retained. Nothing here reads the decision oracle.
"""
from __future__ import annotations
import hashlib, json, re, unicodedata

EVENT_ID_RE = re.compile(r"^EVT-[0-9]{7}$")

# Aliases the audit accepts and folds. Anything not listed is an undeclared
# alias and is rejected rather than repaired (protocol section 6.2).
DECLARED_ALIASES: dict[str, str] = {}


def norm_text(s):
    """NFC-normalise and collapse whitespace. Returns None for a non-string."""
    if not isinstance(s, str):
        return None
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def norm_identifier(s):
    """Upper-case an identifier and fold declared aliases only."""
    t = norm_text(s)
    if t is None:
        return None, s, "NOT_A_STRING"
    u = t.upper()
    if u in DECLARED_ALIASES:
        return DECLARED_ALIASES[u], s, None
    return u, s, None


def canon_identifier_set(values):
    """Sort and de-duplicate an identifier set.

    Returns (sorted_unique, raw, duplicates, undeclared).
    """
    if not isinstance(values, list):
        return None, values, [], []
    out, undeclared, seen, dups = [], [], set(), []
    for v in values:
        c, _raw, err = norm_identifier(v)
        if err is not None:
            undeclared.append(v)
            continue
        if c in seen:
            dups.append(c)
            continue
        seen.add(c)
        out.append(c)
    return sorted(out), values, dups, undeclared


def canonicalise_response(parsed):
    """Canonicalise a parsed model response into the audit's working form.

    Absent optional values become JSON null. The untouched original is kept in
    the `raw_value` side field.
    """
    if not isinstance(parsed, dict):
        return {"parseable": False, "raw_value": parsed}
    reaction, _, _ = norm_identifier(parsed.get("reaction"))
    rule, _, _ = norm_identifier(parsed.get("rule_id"))
    cited, cited_raw, dups, undeclared = canon_identifier_set(parsed.get("decisive_event_ids"))
    reason = norm_text(parsed.get("reason"))
    return {
        "parseable": True,
        "reaction": reaction,
        "rule_id": rule,
        "decisive_event_ids": cited,
        "duplicate_citations": dups,
        "undeclared_citations": undeclared,
        "reason": reason,
        "reason_length_raw": len(parsed["reason"]) if isinstance(parsed.get("reason"), str) else None,
        "extra_fields": sorted(k for k in parsed
                               if k not in ("reaction", "rule_id", "decisive_event_ids", "reason")),
        "raw_value": parsed,
    }


def canonical_json(obj) -> str:
    """Deterministic JSON for hashing: sorted keys, no spacing, NFC text."""
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in sorted(x.items())}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str):
            return norm_text(x)
        return x
    return json.dumps(walk(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_obj(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def prospective_hash(assumption, expected_consequence, assessed_alternative) -> str:
    """Protocol equation (1), degraded to the operands this release records.

    The degradation is declared in contracts/m0_prospective_contract.json.
    """
    return sha256_obj({
        "formation_assumption": norm_text(assumption),
        "expected_consequence": norm_text(expected_consequence),
        "assessed_alternative": norm_text(assessed_alternative),
    })


_TOKEN = re.compile(r"[a-z0-9]+")


def token_set(s):
    return set(_TOKEN.findall((norm_text(s) or "").lower()))


def jaccard(a, b) -> float:
    """Token-set Jaccard. Used for the near-duplicate tests in the L2 contracts."""
    ta, tb = token_set(a), token_set(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
