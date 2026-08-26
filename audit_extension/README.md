# Experiment 1 Audit Extension — implementation

Implements the *Experiment 1 Audit Extension Protocol* (22 August 2026) against the frozen
parent release **v0.5.1-qa1c**. Retrospective, oracle independent, no new model calls.

The audit answers a different question from the parent experiment. The parent experiment asks
whether the model recovered the hidden current meta-decision. This asks whether the retained
artefacts form a complete, coherent, reproducible and challengeable record of the pathway from
visible evidence to output. A trace can be conformant while the decision is wrong, and the
reverse.

## Status, 22 August 2026

- Development splits audited for two models (Terra, Qwen3), 360 calls each.
- **Reserved splits NOT audited.** The protocol section 19 gate is **NO-GO** on one remaining
  condition: the reserved-audit execution authorisation is unsigned. See
  `validation/go_no_go_gate.json`.
- **Protocol section 16, and the independent-reimplementation requirement of section 17,
  are REMOVED for Experiment 1** by decisions E1-H1 and E1-G1. The rest of section 17 stands:
  the deterministic fixtures and canonicalisation tests still run and still pass. Both removals
  are retired as `REMOVED_BY_DECISION`, never deleted and never recorded as satisfied, and both
  carry their declared cost. See `validation/DECISIONS_2026-08-22_round2.json`.
- The protocol freeze is **signed**, delegated: `signed_by` Adrian Lendinez Ibanez on behalf of
  Renxi Qiu. The record says so explicitly.
- 26 decisions applied across two rounds: `validation/DECISIONS_2026-08-22.json` and
  `..._round2.json`. `PROPOSED_AMENDMENTS.md` is superseded and kept only as the record of what
  was originally found.

## The audit takes no human input

Decision E1-H1: the entire audit is independent from human input. No code in the ontology requires
human judgement — verified, not asserted. The consequence is a scope declaration, not a pending
limitation: the audit does **not** assess substantive citation relevance, material scope overreach
beyond its frozen pattern, omitted limitations, or the adequacy of free-text explanation.

Decision E1-G1 removed the independent-reimplementation requirement. Every figure therefore rests
on a single implementation. Fixture agreement, canonicalisation tests and the clean-room test
constrain that implementation; none of them establishes independence from one implementer's
reading of the contracts. The paper must state this.

## Oracle independence

Enforced in code, not asserted. `scripts/auditlib.py` exits rather than open
`scoring_records.jsonl`, anything under `hidden/`, the oracle-bearing context CSVs, or any
object carrying a prohibited field. `scripts/oracle_independence_test.py` builds a clean room
containing only permitted artefacts, verifies no prohibited filename or field is present, runs
the whole pipeline there and compares output hashes with the standard run. It **passes**: every
one of the eight compared outputs is byte identical.

The clean-room context map is taken from `data_v0_5_1/rendering_map.csv`, the release's only
oracle-free context projection. See amendment A5.

## Two readings

Decision A5: **SCOPED is normative**, LITERAL is a declared sensitivity that must never appear as a
headline figure.

The protocol is self-inconsistent on this parent release: section 8.1 says fields the release
does not record must be marked `NOT_RECORDED_IN_SOURCE_RELEASE` and never inferred, while
sections 7.2 and 8.3 make several of those same fields mandatory components. Every metric is
therefore computed twice and carries a `reading` column:

- `LITERAL` — absent canonical fields count as missing mandatory components.
- `SCOPED` — absent canonical fields are recorded but excluded from conformity.

Neither is chosen for the protocol owner. See amendment A4.

## Layout

```
contracts/       frozen check contracts and the machine-readable error ontology
schemas/         JSON Schema for the three machine-readable outputs
mappings/        v0.5.1-qa1c to canonical audit schema, plus the oracle quarantine
fixtures/        15 deterministic validation fixtures with pre-declared expected status
scripts/         the pipeline
results/<label>/ one directory per audited run
validation/      fixture report, clean-room report, gate, hashes, unmet-requirement records
```

## Running it

```bash
REL=~/dca_v051/release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c

# whole pipeline for one executed split
python3 scripts/run_audit.py --release $REL \
    --run ~/dca_v051/bedrock_terra/out/dev_terra \
    --split development --label dev_terra --out results/dev_terra

# protocol section 17: fixtures and canonicalisation (still required)
python3 scripts/validate_fixtures.py --report validation/fixture_report.json

# protocol section 4: clean-room reproduction (release blocker if it fails)
python3 scripts/oracle_independence_test.py --release $REL \
    --run ~/dca_v051/bedrock_terra/out/dev_terra --split development \
    --reference results/dev_terra --report validation/oracle_independence_report.json

# protocol section 19
python3 scripts/go_no_go_gate.py --results results/dev_terra \
    --out validation/go_no_go_gate.json

# rebuild the frozen manifest (excludes the signature and state layer, on purpose)
./scripts/build_manifest.sh
```

The individual protocol-mandated scripts (`build_audit_manifest.py`, `audit_level1_io.py`,
`audit_m0_trace.py`, `audit_b1_trace.py`, `aggregate_audit_results.py`,
`calculate_clustered_intervals.py`, `assign_root_causes.py`, `canonicalise_trace.py`,
`generate_audit_report.py`) each run standalone; `run_audit.py` only sequences them.

## What the audit does and does not score

Deterministic checks only, by design. `E1_CITATION_IRRELEVANT`, `E2_SCOPE_UNDERUSE`,
`E2_LIMITATION_OMITTED` and `E4_QUALIFICATION_OMITTED` are permanently out of scope, and
`E2_SCOPE_OVERREACH` keeps only its frozen automated detector — so it no longer covers material
scope overreach in general, only what its declared pattern matches. That narrowing is declared,
not silent. See `validation/rater_reliability.json`.

Codes whose contract field the parent release does not record are declared inert in the
ontology (`evaluable_in_v0_5_1_qa1c: false`) with the reason recorded, rather than dropped.

## Statistics

Memory group is the independent unit. All contexts, renderings, conditions and audit records
derived from one memory stay in that memory's cluster. Paired memory-clustered bootstrap,
10,000 resamples, two-sided 95% percentile intervals; paired permutation as robustness. With 8
development clusters the intervals are wide and their coverage is optimistic — the parent
release's own coverage study puts 8-cluster coverage near 89.6% against a nominal 95%.

Prediction accuracy and audit results are joined only after both analyses are frozen. No join
is performed anywhere in this package.
