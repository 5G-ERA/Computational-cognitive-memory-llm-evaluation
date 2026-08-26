#!/usr/bin/env python3
"""Shared loading, ontology and case-status machinery for the audit extension.

Oracle independence is enforced here, not assumed: PROHIBITED_BASENAMES and
PROHIBITED_FIELDS are checked on every file this module opens, and any attempt
to read a quarantined artefact raises SystemExit. That is the same defensive
pattern the parent release uses in blind_operational_summary.py.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

import yaml

from canonicalise_trace import norm_text, sha256_obj

HERE = Path(__file__).resolve().parent
PKG = HERE.parent

# ---------------------------------------------------------------- quarantine

PROHIBITED_BASENAMES = {
    "scoring_records.jsonl",
    "canonical_contexts.csv",
    "contexts.csv",
    "contexts_v0_5.csv",
    "oracle_references.jsonl",
    "oracle_references_v0_5_1.jsonl",
    "oracle_references_v0_5.jsonl",
    "latent_states_v0_5.jsonl",
    "latent_episode_states.csv",
}
PROHIBITED_DIRNAMES = {"hidden"}
PROHIBITED_FIELDS = {
    "oracle_reaction", "oracle_rule_id", "oracle_decision", "acceptable_evidence",
    "reaction_correct", "rule_correct", "grounded_correct", "certified_meta_decision",
    "certified_meta_decision_non_confirmatory", "decisive_evidence_hit",
    "historical_evidence_covered", "current_evidence_covered",
    "per_group_decisive_hits", "required_groups_hit", "all_required_groups_covered",
    "decisive_citation_validity", "historical_provenance_hit", "current_provenance_hit",
    "dual_source_provenance_completeness",
}


def guard(path: Path) -> Path:
    p = Path(path)
    if p.name in PROHIBITED_BASENAMES or any(d in PROHIBITED_DIRNAMES for d in p.parts):
        sys.exit(f"ORACLE GUARD: audit code may not read {p}")
    return p


def read_jsonl(path):
    p = guard(path)
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_json(path):
    return json.loads(guard(path).read_text())


def read_csv(path):
    with open(guard(path), newline="") as fh:
        return list(csv.DictReader(fh))


def assert_field_clean(obj, where: str):
    """Fail loudly if a loaded object carries a quarantined field."""
    if isinstance(obj, dict):
        bad = PROHIBITED_FIELDS & set(obj)
        if bad:
            sys.exit(f"ORACLE GUARD: {where} carries prohibited field(s) {sorted(bad)}")


# ---------------------------------------------------------------- ontology

class Ontology:
    def __init__(self, path=None):
        self.raw = yaml.safe_load((path or PKG / "contracts/error_ontology.yaml").read_text())
        self.codes = self.raw["codes"]
        self.priority = {c: i for i, c in enumerate(self.raw["root_cause_priority"])}
        self.version = self.raw["ontology_version"]

    def meta(self, code):
        try:
            return self.codes[code]
        except KeyError:
            sys.exit(f"ONTOLOGY: undeclared error code {code}")

    def severity(self, code):
        return self.meta(code)["severity"]

    def status_effect(self, code):
        return self.meta(code)["status"]

    def domain(self, code):
        return self.meta(code)["domain"]

    def detection(self, code):
        return self.meta(code)["detection"]

    def evaluable(self, code):
        return bool(self.meta(code).get("evaluable_in_v0_5_1_qa1c", True))

    def rank(self, code):
        return self.priority.get(code, 10_000)


# ---------------------------------------------------------------- findings

class Findings:
    """Accumulator for one audited case at one audit level."""

    def __init__(self, ont: Ontology, case: dict, level: str):
        self.ont, self.case, self.level = ont, case, level
        self.errors = []
        self.human_review = False
        self.components_required = 0
        self.components_valid = 0

    def add(self, code, message, check_id=None, evidence=None, reading="BOTH"):
        m = self.ont.meta(code)
        if self.level not in m["scopes"]:
            sys.exit(f"ONTOLOGY: {code} raised outside its declared scopes "
                     f"({m['scopes']}) at level {self.level}")
        self.errors.append({
            "call_id": self.case["call_id"],
            "memory_id": self.case["memory_id"],
            "context_id": self.case["context_id"],
            "canonical_id": self.case["canonical_id"],
            "condition": self.case["condition"],
            "rendering": self.case["rendering"],
            "audit_level": self.level,
            "check_id": check_id,
            "code": code,
            "domain": m["domain"],
            "severity": m["severity"],
            "detection": m["detection"],
            "status_effect": m["status"],
            "message": message,
            "evidence": evidence or {},
            "reading": reading,
        })
        if m["detection"] in ("HUMAN", "HYBRID"):
            self.human_review = True

    def component(self, ok: bool):
        self.components_required += 1
        self.components_valid += 1 if ok else 0

    def completeness(self):
        if not self.components_required:
            return None
        return self.components_valid / self.components_required


STATUS_ORDER = ["NOT_APPLICABLE", "NOT_EVALUABLE", "NONCONFORMANT_CRITICAL",
                "NONCONFORMANT", "INCOMPLETE", "CONFORMANT"]


def case_status(errors, not_applicable=False):
    """Protocol section 10 precedence, applied to a filtered error list."""
    if not_applicable:
        return "NOT_APPLICABLE"
    effects = {e["status_effect"] for e in errors}
    if "NOT_EVALUABLE" in effects:
        return "NOT_EVALUABLE"
    if "NONCONFORMANT_CRITICAL" in effects:
        return "NONCONFORMANT_CRITICAL"
    if "NONCONFORMANT" in effects:
        return "NONCONFORMANT"
    if "INCOMPLETE" in effects:
        return "INCOMPLETE"
    return "CONFORMANT"


def filter_reading(errors, reading, ont: Ontology):
    """Select the errors that belong to one reading of the protocol.

    LITERAL  every raised code counts, including codes whose field the parent
             release does not record (protocol sections 7.2 and 8.3 read as
             mandatory-component requirements).
    SCOPED   codes whose contract field is absent from the parent release are
             recorded but excluded from conformity (protocol section 8.1 read
             as an applicability instruction).
    """
    out = []
    for e in errors:
        if e["reading"] not in ("BOTH", reading):
            continue
        if reading == "SCOPED" and not ont.evaluable(e["code"]):
            continue
        out.append(e)
    return out


# ---------------------------------------------------------------- release

class Release:
    """Read-only view of the frozen parent release, oracle-free by construction."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.response_schema = read_json(self.root / "public/response_schema.json")
        self.rule_vocabulary = read_json(self.root / "public/rule_vocabulary.json")
        self.reaction_enum = set(self.response_schema["properties"]["reaction"]["enum"])
        self.rule_enum = set(self.response_schema["properties"]["rule_id"]["enum"])

        # Context map: taken from rendering_map.csv, the release's only
        # oracle-free context projection. See mappings/ORACLE_QUARANTINE.
        self.context_map = {}
        for r in read_csv(self.root / "data_v0_5_1/rendering_map.csv"):
            assert_field_clean(r, "rendering_map.csv")
            self.context_map[r["context_id"]] = {
                "canonical_id": r["canonical_id"],
                "memory_id": r["memory_id"],
                "rendering": r["render_family"],
            }

        # Source-event registry.
        self.events = {}
        self.memory_events, self.canonical_events = {}, {}
        for e in read_jsonl(self.root / "data_v0_5_1/historical_events.jsonl"):
            self.events[e["id"]] = {"event_id": e["id"], "event_time": e["time"],
                                    "source": e["source"], "content": e["fact"],
                                    "scope": "MEMORY", "owner": e["memory_id"]}
            self.memory_events.setdefault(e["memory_id"], set()).add(e["id"])
        for e in read_jsonl(self.root / "data_v0_5_1/current_events.jsonl"):
            self.events[e["id"]] = {"event_id": e["id"], "event_time": e["time"],
                                    "source": e["source"], "content": e["fact"],
                                    "scope": "CANONICAL_CONTEXT", "owner": e["canonical_id"]}
            self.canonical_events.setdefault(e["canonical_id"], set()).add(e["id"])

        self.split = {r["memory_id"]: r["split"].lower()
                      for r in read_csv(self.root / "data_v0_5_1/split_manifest.csv")}

        self.calls = {}
        for c in read_jsonl(self.root / "prompts/model_calls_v0_5_1.jsonl"):
            assert_field_clean(c, "model_calls_v0_5_1.jsonl")
            assert_field_clean(c["payload"], "model_calls payload")
            self.calls[c["call_id"]] = c

    def owner_memory(self, event_id):
        """Memory that owns an event, resolving current events through their context."""
        e = self.events.get(event_id)
        if e is None:
            return None
        if e["scope"] == "MEMORY":
            return e["owner"]
        for ctx in self.context_map.values():
            if ctx["canonical_id"] == e["owner"]:
                return ctx["memory_id"]
        return None


class Run:
    """Read-only view of one executed split. scoring_records.jsonl is quarantined."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.raw = {r["call_id"]: r for r in read_jsonl(self.root / "responses_raw.jsonl")}
        self.parsed = {r["call_id"]: r for r in read_jsonl(self.root / "responses_parsed.jsonl")}
        self.terminal = {r["call_id"]: r for r in read_jsonl(self.root / "call_registry.jsonl")}
        self.manifest = read_json(self.root / "run_manifest.json")
        for d, name in ((self.raw, "responses_raw"), (self.parsed, "responses_parsed"),
                        (self.terminal, "call_registry")):
            for v in list(d.values())[:1]:
                assert_field_clean(v, name)


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["Ontology", "Findings", "Release", "Run", "case_status", "filter_reading",
           "read_json", "read_jsonl", "read_csv", "guard", "sha256_file", "sha256_obj",
           "norm_text", "PROHIBITED_BASENAMES", "PROHIBITED_FIELDS", "PKG"]
