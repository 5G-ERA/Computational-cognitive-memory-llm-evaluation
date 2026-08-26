# Proposed amendments to the Experiment 1 Audit Extension Protocol

> **SUPERSEDED, 22 August 2026.** All eight amendments were put to Renxi Qiu as questions A1-A8
> and all eighteen questions were answered and applied the same day. This file is retained as the
> record of what was found and why, with the pre-decision measurements. **It is not the current
> state of the audit.** For that, see `validation/DECISIONS_2026-08-22.json` (the eighteen answers
> and where each landed) and `results/*/audit_report.md` (the post-decision numbers).

Status at the time of writing: **proposed, not applied.** The implementation in this package follows the protocol
exactly as written. Every number in `results/` is produced by the unamended protocol. Each
amendment below is a decision for the protocol owner before freeze.

Evidence is from the two development splits (8 memory groups, 360 calls each) of the frozen
parent release v0.5.1-qa1c. The reserved splits were not audited: the section 19 gate is
**NO-GO** (see `validation/go_no_go_gate.json`).

---

## A1 — `E4_INFLUENCE_UNEXPLAINED` decides the primary Level 1 estimand and its detector is prose style

**Protocol text.** Section 6.5 requires the audit to check the grounds a response claims.
`E4_INFLUENCE_UNEXPLAINED` (section 9, domain E4, severity MAJOR) covers a response that gives
no stated ground for the influence the memory exerted. The only oracle-independent detector
available on this parent release is whether the free-text `reason` names an event identifier:
the release publishes no structured grounds field.

**What was measured.**

| detector state | model | B0 | M0 | B1 | ΔIO = B1 − B0 (95% CI) |
|---|---|---|---|---|---|
| check active | Terra | 0.00% | 0.00% | 0.00% | +0.00 [+0.00, +0.00] |
| check active | Qwen3 | 87.50% | 85.83% | 75.83% | **−11.67 [−20.00, −2.50]** |
| check removed | Terra | 99.17% | 99.17% | 100.00% | +0.83 [+0.00, +2.50] |
| check removed | Qwen3 | 97.50% | 98.33% | 97.50% | +0.00 [−2.50, +2.50] |

The check fires on 360 of 360 Terra cases and 54 of 360 Qwen3 cases. Terra never quotes an
event identifier inside `reason`; Qwen3 usually does. The check therefore separates two models'
writing habits, not two conditions' auditability — and on Qwen3 it is the sole reason the
primary Level 1 estimand excludes zero, in the direction **against** cognitive memory.

**Risk if unamended.** The main paper would report a significant negative Level 1 result for
cognitive memory that disappears entirely when one style-dependent check is removed.

**Proposed amendment.** Demote `E4_INFLUENCE_UNEXPLAINED` to severity `INFO`, status effect
`NONE`, detection `HYBRID`, and report it descriptively as a reporting-style statistic. Its
deterministic content is already carried by `E0_SCHEMA_INVALID` (empty `decisive_event_ids`)
and by `E1_CURRENT_GROUNDS_MISSING` / `E1_HISTORICAL_GROUNDS_MISSING`.

---

## A2 — Level 1 conformity is at ceiling once A1 is applied, so ΔIO cannot discriminate

With `E4_INFLUENCE_UNEXPLAINED` demoted, deterministic Level 1 conformity is 97.5%–100% in
every condition for both models. This is structural, not incidental: the parent release's
public response schema has four fields, and the frozen runner already rejects schema-invalid
responses, so almost any response that reaches the audit is Level 1 conformant.

**Proposed amendment.** Either (i) declare ΔIO a **negative-control / instrument-integrity**
endpoint rather than a discriminating one and state the ceiling explicitly in the paper, or
(ii) drop ΔIO from the confirmatory set. Option (i) is recommended: a ceiling on ΔIO is itself
the correct evidence that the retained artefacts support reconstruction in every condition,
which is a claim the paper can make.

---

## A3 — Section 8.3 makes the UNRESOLVED verification family critical by construction

**Protocol text.** Section 8.3: "Missing B1 consequence closure or constitutive linkage is
critical." Section 10 lists "absent B1 constitutive evidence" as critical.

**What was measured.** Exactly 10 of the 40 memories carry `constitutive_event_ids: []`. Those
10 are precisely the 10 memories whose verification state is `UNRESOLVED` — one per assumption
family, by design of the parent release. An unresolved verification has no constitutive
evidence *because it was never resolved*; that is its resolved state.

Consequence, on both development splits: `E3_CONSTITUTIVE_LINK_MISSING` fires on 2 of 8
memories, that is 30 of 120 B1 cases, giving a **B1 critical rate of 25.00%** and

| contrast | Terra | Qwen3 |
|---|---|---|
| ΔTrace = B1 − M0 (SCOPED) | −25.00 [−62.50, +0.00] | −25.83 [−62.50, −0.83] |
| ΔCritical = B1 − M0 | +25.00 [+0.00, +62.50] | +25.00 [+0.00, +62.50] |

The two models agree to within 0.83 pp because the quantity is a fixed property of the
dataset, not of either system. In the reserved split the same family covers 8 of 32 memories,
so the artefact reproduces at exactly 25%.

**Proposed amendment.** Add a structural status `UNRESOLVED_BY_CONDITION_DESIGN`, symmetric
with the `OPEN_LOOP_BY_CONDITION_DESIGN` carve-out the protocol already grants M0 in section
7.2. When the retained relation records unresolvedness, absent constitutive evidence is that
relation's content and must not raise `E3_CONSTITUTIVE_LINK_MISSING`. The audit should instead
check the positive obligation: that the unresolvedness is *represented* rather than silently
dropped, which `E2_UNRESOLVED_COLLAPSED` already covers.

---

## A4 — The principal Level 2 estimand is degenerate on this parent release

**Protocol text.** Section 8.1: fields absent from the original release "must be marked
`NOT_RECORDED_IN_SOURCE_RELEASE`; they must not be inferred". Sections 7.2 and 8.3 list several
of those same fields as mandatory components whose absence is MAJOR or CRITICAL.

The two instructions conflict on v0.5.1-qa1c, which records neither `attributed_capability_id`,
`evidence_contract_id`, `verification_window`, `represented_function_id`,
`resolved_consequence_status`, `semantic_scope_status`, `current_relation`, `predecessor_id`
nor `semantic_version` — in either memory object. This implementation computes both readings.

| reading | Conformity M0 (L2) | Conformity B1 (L2) | Critical rate B1 | ΔTrace |
|---|---|---|---|---|
| LITERAL | 0.00% | 0.00% | 100.00% | **+0.00 [+0.00, +0.00]** |
| SCOPED | 100.00% | 74–75% | 25.00% | −25 (see A3) |

Under LITERAL, ΔTrace is exactly zero with a zero-width interval in both models: the estimand
cannot move. Under SCOPED, it is the A3 artefact. Neither reading measures a system property.

The deeper cause is that **the parent release has no trace-writing path.** The M0 and B1
objects are delivered *to* the model inside the payload; the model returns only `reaction`,
`rule_id`, `decisive_event_ids` and `reason`. Level 2 as specified therefore audits the
dataset, which is identical across all five contexts, all three renderings and all models —
`results/*/reproducibility_report.json` confirms invariance for every memory.

**Proposed amendment.** Choose one:

1. **Report Level 2 as a release-integrity audit.** Rename the estimand: Level 2 certifies that
   the retained cognitive-memory artefacts are complete, coherent and non-rewritten. Report it
   once for the release, not as a per-condition contrast, and drop equation (7). This is
   implementable today and is what the current numbers actually support.
2. **Add a trace-response object and re-run.** Extend the public response schema so B1 and M0
   return the resolution state, the constitutive evidence they relied on, the current relation
   they judged to hold and the grounds for current use. Then equation (7) measures a system
   property. This requires new model calls and a new prospectively frozen protocol; section 21
   already anticipates a separate extension of this kind.

Option 1 is recommended for the present paper, with option 2 declared as the follow-on.

---

## A5 — Oracle-bearing files sit outside `hidden/`

`data_v0_5_1/canonical_contexts.csv` carries `oracle_reaction` and `oracle_rule_id`;
`data_v0_5_1/contexts.csv` and `data/contexts_v0_5.csv` carry `oracle_reaction`. These are the
naturally named sources for the canonical-context to memory mapping that section 6.1 requires,
so a section 4 clean room built by excluding only `hidden/` imports the oracle.

The release does ship an oracle-free alternative, `data_v0_5_1/rendering_map.csv`, and this
implementation uses only that. The delivered payloads themselves are clean: zero occurrences of
the token `oracle` in `prompts/model_calls_v0_5_1.jsonl`.

**Proposed amendment.** Name the quarantine explicitly in the frozen protocol, as
`mappings/v0_5_1_qa1c_to_audit_schema.json` now does, rather than leaving the clean-room
boundary to be inferred from a directory name.

---

## A6 — Section 3 requires a rendering identifier the release does not record

Call envelopes carry `context_id` but no `rendering` field; the rendering is the suffix of
`context_id` (`-STR`, `-CHR`, `-CON`). The manifest derives it, and the derivation is declared
in the mapping file. **Proposed amendment:** record the derivation rule in the protocol so two
implementations cannot disagree about it.

---

## A7 — Two section 19 gate conditions cannot be met by this package alone

`independent_validator_agreement_100pc` needs a second implementation written from
`contracts/` and `schemas/` by an implementer who does not read `scripts/`.
`human_review_rubric_and_blinding_frozen` needs a frozen rubric and a coded development sample.
Until both exist, every conformity figure in `results/` is a **deterministic-only** conformity,
and adding the human layer can only lower it. Both are recorded as unmet in
`validation/implementation_agreement.json` and `validation/rater_reliability.json`.

---

## A8 — "audit conformity" here is not equation (36) of the theory paper

*A Computational Theory of Cognitive Memory* V4.7 defines audit conformity as

> AuditConformant_t = 1 ⟺ κ_t^life ≡_audit κ_t^life,⋆ ∧ CriticalViolation_t = 0

that is, the realised lifecycle trace matches an **independently specified frozen reference
certificate**. The theory's own ordering is: *audit-ready* (required trace fields retained) →
*evaluable* (frozen reference exists) → *functionally auditable* (pathway reconstructible) →
*audit-conformant* (reconstructed pathway matches the reference).

This extension is oracle independent by design, so it has no reference certificate to match
against. What it measures is the **third** rung, functional auditability, plus internal
coherence of the system's own stated pathway. That is exactly what the protocol's own section 1
says, and it is the right thing to measure here — but the two constructs must not share a name
in the paper, or a reader will take Level 1 and Level 2 conformity for equation (36).

Note also that the theory's audit apparatus is specified for the deployment pathway of
Experiment 2, where the system writes a lifecycle trace. Experiment 1 has no trace-writing
path, which is the structural reason behind amendment A4.

**Proposed amendment.** Rename the extension's outcomes to *trace reconstructibility* and
*trace coherence*, reserve *audit conformity* for equation (36), and state the distinction
wherever both appear.
