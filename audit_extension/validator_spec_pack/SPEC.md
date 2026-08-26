# Independent validator — build brief

> **REVISION, 22 August 2026, later the same day. If you already started, re-read this.**
> Renxi Qiu answered all eighteen open questions and the contracts changed under you.
> `contracts/` is now **L1-IO-1.2, L2-M0-1.2, L2-B1-1.2, CRIT-1.1, AUDIT-ONT-1.1**, plus a new
> `contracts/terminology_audit.json`. `DECISIONS_2026-08-22.json` in this pack records all
> eighteen answers and names, for each one, the contract it landed in. The changes that touch
> your implementation most:
>
> - **A1** `E4_INFLUENCE_UNEXPLAINED` is now INFO with **no case-status effect**. It is still
>   emitted; it just cannot make a case non-conformant.
> - **A3** new structural status `UNRESOLVED_BY_CONDITION_DESIGN`. A B1 relation that positively
>   represents unresolvedness must **not** raise `E3_CONSTITUTIVE_LINK_MISSING`. The detector is
>   spelled out in `contracts/b1_resolved_contract.json → unresolved_by_condition_design`. Note
>   the negative half: an empty constitutive set *without* that positive representation is still
>   a critical violation. Two blind fixtures cover both halves.
> - **B6** the prospective-hash test is no longer a non-rewrite claim. `E5_PROSPECTIVE_REWRITE`
>   is INFO, inert on this release, and reported as *partial prospective field stability*.
> - **A5** `SCOPED` is normative and `LITERAL` is a sensitivity. Emit both exactly as before;
>   only the reporting order and labelling changed.
> - **B2, B3, B10** renames. `payload_registry_complete`, `payload_evidence_cutoff`, and the
>   outcome names in `contracts/terminology_audit.json`. None of these change a computation.
>
> The blind fixtures are now **15**, not 13.

Protocol §17 requires a second implementation of the Experiment 1 audit that reproduces
deterministic error codes, critical status, case status and aggregate counts. A re-run of the
first implementation is not independence, so this pack is the whole of what you get.

## The rule that makes this worth doing

**Do not open `audit_extension/scripts/`, `results/`, `validation/`, or
`PROPOSED_AMENDMENTS.md`.** Everything you need is in this directory. If something here is
ambiguous, that ambiguity is a finding — record it and ask, do not go and look at how the first
implementation resolved it. A question you raise is worth more to the release than a matching
number you obtained by peeking.

Also excluded, and for a different reason: `contracts/` names files that carry the decision
oracle. `mappings/v0_5_1_qa1c_to_audit_schema.json → ORACLE_QUARANTINE` lists them. Your
implementation must not read any of them, nor `scoring_records.jsonl`, nor anything under
`hidden/`. Build the guard in from the start rather than bolting it on.

## What you build

A pipeline that, for one executed split, emits two files:

| file | schema |
|---|---|
| `audit_errors.jsonl` | `schemas/audit_error.schema.json`, one row per finding |
| `audit_case_summaries.jsonl` | `schemas/audit_case_summary.schema.json`, one row per (case, audit level, reading) |

Nothing else is compared. Report generation, CSV rollups, bootstrap intervals — skip them.

## Inputs

From the frozen release
`release_qa1c/medical_assumption_memory_computational_benchmark_v0_5_1_qa1c`:

- `prompts/model_calls_v0_5_1.jsonl` — the immutable payloads, one per expected call
- `public/response_schema.json`, `public/rule_vocabulary.json`
- `data_v0_5_1/historical_events.jsonl`, `data_v0_5_1/current_events.jsonl` — source-event registry
- `data_v0_5_1/rendering_map.csv` — the **only** oracle-free context map; see A5 in the mapping file
- `data_v0_5_1/split_manifest.csv`

From an executed run directory (`bedrock_terra/out/dev_terra`, `bedrock_terra/out/dev_qwen3`):

- `responses_raw.jsonl`, `responses_parsed.jsonl`, `call_registry.jsonl`, `run_manifest.json`

Expected calls for `--split development`: **360 per run, 8 memory groups.**

## The specification, in reading order

1. `protocol/experiment1_audit_protocol_source.pdf` — normative. Read §§4–13 and §17 closely.
2. `contracts/error_ontology.yaml` — 40 codes. Each declares its scopes, severity, detection
   mode, case-status effect, and whether the parent release records the field it needs
   (`evaluable_in_v0_5_1_qa1c`). **A code raised outside its declared scopes must abort your
   run, not warn.**
3. `contracts/level1_io_contract.json` (L1-IO-1.2) — every Level 1 check, with its identifier,
   its code, and its operational definition. Canonicalisation is specified here including the
   order of operations.
4. `contracts/m0_prospective_contract.json` (L2-M0-1.2) and
   `contracts/b1_resolved_contract.json` (L2-B1-1.2) — the two Level 2 contracts, the field
   mapping, and which canonical fields this release does not record.
5. `contracts/critical_violations.json` (CRIT-1.1) — the critical list and the §10 case-status precedence.
6. `contracts/agreement_contract.json` — **read this before writing code.** It fixes the
   conventions that would otherwise be implicit: how the two readings are folded, how root
   causes are selected, what "evaluable" and "reconstructible" mean, one row per finding rather
   than one per identifier, and what happens on an unparseable response or a missing artefact.
7. `contracts/terminology_audit.json` — the canonical names. Internal metric keys are
   unchanged, so this does not affect what you compute; read it so your notes use the same
   words as the reports.
8. `mappings/v0_5_1_qa1c_to_audit_schema.json` — release paths, identifier derivations (note
   that `rendering` is derived from the `context_id` suffix), and the oracle quarantine.

## Two readings, both required

Every case is scored twice. `LITERAL` counts a canonical field the release does not record as a
missing mandatory component; `SCOPED` records it but excludes it from conformity. The exact fold
is in `agreement_contract.json → conventions_that_would_otherwise_be_implicit.reading_filter`.
Emit both; the `reading` field on each row says which.

Expect `LITERAL` to look strange. It is supposed to. Report what the contracts produce.

## Warm-up: the blind fixtures

`fixtures_blind/` holds 15 self-contained case bundles — a small synthetic registry, one
payload, one response, one manifest row. The expected statuses and codes have been stripped, so
they test you rather than tell you. Each bundle names its `audit_level`; run only that level on
it. Getting 15/15 before touching the real runs will save you a lot of time.

`b0_level2_not_applicable.json` is at level `L2_B0`, which raises no error and emits one case
row with status `NOT_APPLICABLE`.

## Acceptance

```bash
python3 audit_extension/scripts/compare_implementations.py \
    --reference audit_extension/results/dev_terra  --candidate <yours>/dev_terra \
    --reference audit_extension/results/dev_qwen3  --candidate <yours>/dev_qwen3 \
    --validator "Adrian Lendinez Ibanez, independent implementation" \
    --report audit_extension/validation/implementation_agreement.json
```

That script compares only the four must-agree dimensions and names the offending cases when they
differ. It does not privilege the reference: a disagreement means the two implementations differ,
and which one is wrong is then a joint decision. Run it only when you are done — reading its
output early turns your implementation into a copy of the other one.

Agreement must be **100%** on all four dimensions across both runs to clear the §19 gate
condition `independent_validator_agreement_100pc`.

## Where the two of us are most likely to diverge

Not a hint list — these are the places where the contract language is doing the most work, and
where a genuine disagreement would be most informative:

- the fold from `BOTH` rows into the two readings, and whether a code that is inert on this
  release still appears in the `LITERAL` view;
- whether a check that finds three bad identifiers emits one row or three;
- the interaction between `E0_INPUT_TRUNCATED` and `E1_CITATION_NOT_VISIBLE` when a registered
  record is withheld from a payload — the precedence in §10 decides the case status;
- whether `E4_REVIEW_DEFER_CONFLATED` can fire without `E4_RULE_OUTCOME_INCONSISTENT` also
  firing, given each rule admits exactly one reaction;
- `E5_VERSION_AMBIGUOUS` versus `E5_PROSPECTIVE_REWRITE` when the prospective relation differs
  and a successor is declared;
- whether the `UNRESOLVED_BY_CONDITION_DESIGN` exemption suppresses only
  `E3_CONSTITUTIVE_LINK_MISSING` or also the constitutive-ownership and visibility checks that
  follow it.

If your reading of the contract differs from mine on any of these, say so before we compare.
That is the disagreement worth having.
