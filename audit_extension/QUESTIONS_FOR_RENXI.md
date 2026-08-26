# Experiment 1 Audit Extension — open questions

**To:** Renxi Qiu
**Re:** Audit extension protocol of 22 August 2026, implemented against release v0.5.1-qa1c
**Status:** package built and tested; §19 gate is NO-GO; reserved splits untouched

The extension is implemented in full and runs oracle-free: 13/13 deterministic fixtures agree
on status and codes, and the §4 clean-room test reproduces all eight outputs byte for byte in a
directory containing no oracle artefact. It has been run on the development splits of two models
(Terra and Qwen3, 360 calls each). Nothing has been applied to the protocol and no reserved
split has been audited.

The questions below fall into three groups. Group A changes what the protocol measures and needs
your decision. Group B are places where the protocol is silent, where I had to choose, and where
I need your ratification — these matter now because Adrian is writing the independent §17
validator from the contracts, and an unratified convention will make his implementation disagree
with mine for reasons that are not defects. Group C is scope.

---

## Group A — Decisions that change what is measured

### A1. Should `E4_INFLUENCE_UNEXPLAINED` be demoted to INFO?

The release publishes no structured grounds field, so the only oracle-independent detector for
this code is whether the free-text `reason` quotes an event identifier. Terra never does; Qwen3
usually does. The check fires on 360/360 Terra cases and 54/360 Qwen3 cases.

| check | model | B0 | M0 | B1 | ΔIO = B1 − B0, 95% CI |
|---|---|---|---|---|---|
| active | Terra | 0.00% | 0.00% | 0.00% | +0.00 [+0.00, +0.00] |
| active | Qwen3 | 87.50% | 85.83% | 75.83% | **−11.67 [−20.00, −2.50]** |
| removed | Terra | 99.17% | 99.17% | 100.00% | +0.83 [+0.00, +2.50] |
| removed | Qwen3 | 97.50% | 98.33% | 97.50% | +0.00 [−2.50, +2.50] |

One check, whose detector is prose style, is the sole reason the primary Level 1 estimand
excludes zero — in the direction against cognitive memory.

**Recommendation: yes, demote to INFO and report descriptively.** Its deterministic content is
already carried by `E0_SCHEMA_INVALID` and by the two grounds-missing codes.

### A2. Should ΔIO be declared an instrument-integrity endpoint rather than a discriminating one?

With A1 applied, deterministic Level 1 conformity is 97.5%–100% in every condition for both
models. This is structural: the public response schema has four fields and the frozen runner
already rejects schema-invalid responses, so nearly any response reaching the audit is Level 1
conformant. The ceiling is the same shape as the one we found in the Terra decision arm.

**Recommendation: keep ΔIO, declare the ceiling explicitly, and report it as evidence that the
retained artefacts support reconstruction in every condition** — which is a claim the paper can
make — rather than as a contrast expected to move.

### A3. Should `UNRESOLVED_BY_CONDITION_DESIGN` be added, so §8.3 stops making the UNRESOLVED family critical?

Exactly 10 of 40 memories carry `constitutive_event_ids: []`. They are exactly the 10 whose
verification state is `UNRESOLVED`, one per assumption family, by design. An unresolved
verification has no constitutive evidence because it was never resolved; that is its resolved
state. §8.3 calls this a critical violation.

| contrast (SCOPED reading) | Terra | Qwen3 |
|---|---|---|
| ΔTrace = B1 − M0 | −25.00 [−62.50, +0.00] | −25.83 [−62.50, −0.83] |
| ΔCritical = B1 − M0 | +25.00 [+0.00, +62.50] | +25.00 [+0.00, +62.50] |
| B1 critical rate | 25.00% | 25.00% |

Two different models agree to within 0.83 pp because the quantity is a property of the dataset,
not of either system. The reserved split holds 8 of 32 such memories, so it reproduces at exactly
25% there too.

**Recommendation: yes.** The carve-out is symmetric with the `OPEN_LOOP_BY_CONDITION_DESIGN`
exemption §7.2 already grants M0. The positive obligation — that unresolvedness is represented
rather than dropped — is already covered by `E2_UNRESOLVED_COLLAPSED`.

### A4. Level 2 as a release-integrity audit now, or extend the response schema and re-run?

§8.1 requires fields absent from the release to be marked `NOT_RECORDED_IN_SOURCE_RELEASE` and
never inferred. §7.2 and §8.3 make several of those same fields mandatory components. The two
instructions conflict on this release, so both readings are computed:

| reading | M0 L2 conformity | B1 L2 conformity | B1 critical | ΔTrace |
|---|---|---|---|---|
| LITERAL | 0.00% | 0.00% | 100.00% | **+0.00 [+0.00, +0.00]** |
| SCOPED | 100.00% | 74–75% | 25.00% | −25 (the A3 artefact) |

Under LITERAL the estimand has a zero point and a zero-width interval in both models: it cannot
move. Under SCOPED it is the A3 artefact. Neither reading measures a system property.

The cause is structural rather than editorial. **The release has no trace-writing path.** The M0
and B1 objects are delivered *to* the model inside the payload; the model returns only
`reaction`, `rule_id`, `decisive_event_ids` and `reason`. Level 2 as specified therefore audits
the dataset, which the §14 checks confirm is invariant across all five contexts, all three
renderings and both models, for every memory. This is also why the protocol reads as if written
for Experiment 2, where the system writes a lifecycle trace κ_t and equation (36) compares it
with a frozen reference certificate. Experiment 1 has no κ_t.

**Recommendation: report Level 2 as a release-integrity audit for this paper** — the retained
artefacts are complete, coherent and non-rewritten, stated once for the release — **and drop
equation (7)**, declaring the schema extension as the §21 follow-on.

### A5. Which reading is normative for the paper, LITERAL or SCOPED?

Both are computed and both are in `results/`. Only one can appear as the headline. This is
partly consequential on A4: under recommendation A4, SCOPED is the natural choice and LITERAL
becomes a declared sensitivity.

### A6. Will you sign the freeze record?

The third unmet §19 gate condition. All 83 files are hashed in
`validation/SHA256SUMS.txt`. No signature record has been created — I will not write one that
names you unless you sign it.

---

## Group B — Specification points needing ratification

These are places where the protocol does not determine an implementation. I made a choice in each
case and recorded it in the contracts and in `protocol/experiment1_audit_protocol.tex`. They need
your ratification **before** the independent validator's results mean anything: an unratified
convention produces a disagreement that is about the specification, not about either
implementation.

**B1 — Rendering identifier (§3).** The release records no rendering field on the call envelope.
Rendering is derived from the `context_id` suffix: `-STR` → STRUCTURED, `-CHR` → CHRONOLOGICAL,
`-CON` → CONCISE. Ratify the derivation as part of the frozen protocol?

**B2 — "Scientifically truncated" request (§6.1).** Implemented as: the payload carries every
longitudinal record registered for the memory and every current record registered for the
canonical context. Verified to hold for all 1800 expected calls. Ratify?

**B3 — Decision boundary (§6.4).** Implemented as `max(event_time)` over the current records
delivered in that payload. The protocol names the boundary but does not define it. Ratify?

**B4 — Self-declared grounds categories (§6.5).** The release publishes no structured grounds
field, so the six categories cannot be read off the response. I implemented three deterministic
obligations — current applicability requires a cited current record; a historical rule requires a
cited longitudinal record; and the influence-explanation check of A1 — and deferred the rest to
the human rubric rather than approximating them with text heuristics. Ratify the reduction?

**B5 — "Current event represented as formation evidence" (§6.6).** There is no oracle-free
deterministic detector for this on the present release; the claim lives in free text. I deferred
it to the frozen human rubric and it raises nothing today, rather than approximating it. Ratify?

**B6 — Prospective integrity hash (§7.3).** Equation (1) is h_pre = Hash(H, r, K, Γ, V). Three of
the five operands — attributed capability, evidence contract and verification window — are not
recorded by this release. The hash is computed over the three that exist, and the §8.2
non-rewrite test inherits that weakening. Ratify the degraded hash, or withdraw the non-rewrite
test as unevaluable on this release?

**B7 — Competing evidence (§8.4).** The release declares
`competing_or_unresolved_event_ids` but states no expectation of when it must be non-empty, so
the check is recorded as `NOT_EVALUABLE_FROM_SOURCE_RELEASE`, exactly as §8.4 directs. Reference
integrity of the field is still checked. Confirm?

**B8 — Human-detected codes (§16).** Four codes are declared inert pending a frozen rubric —
`E1_CITATION_IRRELEVANT`, `E2_SCOPE_UNDERUSE`, `E2_LIMITATION_OMITTED`,
`E4_QUALIFICATION_OMITTED` — and `E2_SCOPE_OVERREACH` is scored by its automated half only. This
means every conformity figure currently in `results/` is a **deterministic-only** figure and
therefore an upper bound: adding the human layer can only lower it. Confirm the list, and confirm
that the paper will state the upper-bound caveat?

**B9 — Cluster coverage (§15).** The development splits give 8 memory clusters. Our own coverage
study puts 8-cluster bootstrap coverage near 89.6% against a nominal 95%, and 32-cluster coverage
near 92.5%. Confirm that every audit interval carries the same coverage disclosure the decision
results already carry?

**B10 — Naming (§1 versus theory equation 36).** V4.7 defines audit conformity as the realised
lifecycle trace matching an independently specified frozen reference certificate. This extension
is oracle-independent by design and has no certificate to match, so it measures the rung below:
functional auditability plus internal coherence of the system's own stated pathway. That is what
§1 of the protocol says it does. Should the extension's outcomes be renamed — *trace
reconstructibility* and *trace coherence* — with *audit conformity* reserved for equation (36),
so the two constructs are not conflated in the paper?

---

## Group C — Scope

**C1 — Does the audit extend to the Kimi arm?** The Kimi reserved run (1440 calls, August 2026)
has every artefact the audit needs. I verified that all six audit inputs — payloads, both event
registries, the context map, the response schema and the rule vocabulary — are byte-identical
between qa1b and qa1c, so the run is auditable against the qa1c contracts without a version
mismatch. It would give a third model, but only at the reserved level: there is no comparable
Kimi development run. Include it, and if so under what authorisation?

**C2 — Reserved audit authorisation.** §19 is NO-GO and reserved audit execution is not
authorised. Three mandatory conditions are unmet: the independent validator (Adrian is writing
it now from the contracts alone), the human-review rubric and blinding, and the signed freeze.
When those are met, does reserved audit execution need its own authorisation record naming the
run, as reserved *execution* did — or does the frozen protocol plus your signature suffice?

---

## What is not blocked

One result needs no decision and survives every amendment above. The §14 cross-rendering check
required no new calls:

| model | condition | reaction agree | rule agree | citation set exact | citation Jaccard |
|---|---|---|---|---|---|
| Terra | B0 | 95.0% | 95.0% | 85.0% | 0.931 |
| Terra | M0 | 100.0% | 100.0% | 82.5% | 0.936 |
| Terra | B1 | 97.5% | 97.5% | 82.5% | 0.947 |
| Qwen3 | B0 | 80.0% | 80.0% | 50.0% | 0.746 |
| Qwen3 | M0 | 82.5% | 82.5% | 67.5% | 0.816 |
| Qwen3 | B1 | 72.5% | 67.5% | **17.5%** | **0.592** |

For Qwen3, giving the model more retained memory makes *which evidence it cites* markedly less
stable to how the same records are worded — citation sets agree exactly in half of B0 contexts
but in under a fifth of B1 contexts — while the decision itself stays comparatively stable. Terra
shows no such spread. This is an oracle-free property of the interface and belongs in the
supplement whatever is decided about Levels 1 and 2.
