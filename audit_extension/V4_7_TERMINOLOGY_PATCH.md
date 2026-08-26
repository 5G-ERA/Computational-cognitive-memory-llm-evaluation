# V4.7 terminology patch — drafted

**Decision:** E1-F2, Renxi Qiu, 22 August 2026: *DRAFT AND APPLY IT.*
**Status:** drafted, revised after the reserved audit. **Not applied** — the LaTeX source of V4.7 is not on this machine, only the
PDF. Send the `.tex` and this becomes a one-pass edit.
**Basis:** decision B10 reserves *audit conformity* for equation (36); decision E1-F1 fixes the
Experiment 1 audit claim and its placement.

---

## Finding first: nothing in V4.7 is currently wrong

Every occurrence of *audit conformity* in V4.7 refers correctly to the Experiment 2 lifecycle
certificate test. There are four:

| Location | Text | Verdict |
|---|---|---|
| Discussion, p. 11 | "audit conformity compares the lifecycle with the frozen reference" | Correct, and a usable definition |
| Methods, *Explanation, governance and parallel functional audit* | Equation (36) and the four-rung ordering | Correct |
| Same section | "prevented audit conformity regardless of the scalar score" | Correct |
| Experimental evaluation | "Parallel functional-evaluation endpoints comprised lifecycle reconstructibility, audit conformity and critical violations" | Correct |

**So this patch is preventive, not corrective.** The risk appears only when the Experiment 1 audit
extension enters the manuscript. At that point a reader meets two things called *reconstructibility*
and two things that look like *audit conformity*, and nothing in the current text tells them apart.
The patch must land **before** the Experiment 1 audit text, not after.

---

## Patch 1 — Terminology guard (ADD)

**Where:** Methods, section *Explanation, governance and parallel functional audit*, immediately
after the sentence ending "...distinct from factual correctness and beneficial action."

**Add:**

> These audit terms are reserved for the deployment pathway, where the system writes a lifecycle
> trace and an independently specified frozen reference certificate exists. The retrospective
> functional audit of Experiment 1 has no such certificate: it is oracle independent by design and
> therefore reaches only the third rung of this ordering. Its outcomes are reported as
> *input–output trace reconstructibility* and *cognitive-trace coherence*, never as audit
> conformity.

**Why:** this is the single load-bearing sentence. It uses the paper's own four-rung ordering
(audit-ready → evaluable → functionally auditable → audit-conformant) to place Experiment 1
precisely, instead of asserting a distinction by fiat.

---

## Patch 2 — Disambiguate the two reconstructibilities (EDIT)

The word carries two different meanings once Experiment 1's audit is in.

**2a. Experimental evaluation section.**

- Current: "Parallel functional-evaluation endpoints comprised lifecycle reconstructibility, audit
  conformity and critical violations."
- Replace with: "Parallel functional-evaluation endpoints for the deployment pathway comprised
  lifecycle reconstructibility, audit conformity and critical violations."

**2b. Discussion, p. 11.**

- Current: "Functional reconstructibility recovers the pathway; decision preservation evaluates its
  outcome; governed-reference recovery includes the required grounds; and audit conformity compares
  the lifecycle with the frozen reference."
- Replace with: "Functional reconstructibility recovers the pathway; decision preservation
  evaluates its outcome; governed-reference recovery includes the required grounds; and audit
  conformity compares the lifecycle with the frozen reference. Where no frozen reference exists,
  as in the retrospective audit of Experiment 1, reconstructibility and coherence can be
  established but conformity cannot."

**Why:** unqualified, "lifecycle reconstructibility" and "input–output trace reconstructibility"
are one word apart and mean different things at different levels of assurance.

---

## Patch 3 — Main-paper statement for the Experiment 1 audit (ADD)

**Decision E1-F1:** supplement, with a short main-paper methods or results statement. This is that
statement. Place it in Results, after the Experiment 1 decision result.

> A retrospective functional audit of the Experiment 1 artefacts was performed, oracle
> independently and without new model calls (Supplementary Note N). On the reserved splits,
> deterministic input–output trace reconstructibility was 95.8–99.8% across conditions and models
> and cognitive-trace coherence 98.8–100%, with two critical violations in 4,800 audited cases,
> both arising from a single memory. No condition difference was statistically supported in either
> model. The audit establishes deterministic trace reconstructibility and representation
> integrity; it does not establish superior model-level auditability for cognitive memory.

**Note the last clause.** It is what decision E1-F1 requires, and it is the sentence that stops a
reader inferring a comparative claim from a ceiling.

---

## Patch 4 — Supplementary Note (NEW)

Full text drafted below. Keep it in the supplement per E1-F1.

### Supplementary Note N. Retrospective functional audit of Experiment 1

**Aim.** The decision experiment measured whether the model recovered the hidden current
meta-decision. This audit measures a different property: whether the retained artefacts form a
complete, coherent and challengeable record of the pathway from visible evidence to output. A trace
can be reconstructible while the decision is wrong, and the reverse.

**Independence.** The audit reads only the delivered payloads, the immutable provider responses,
the terminal and parsed records, the public schemas and the source-event registry. It never reads
the hidden reaction, the hidden rule, the correctness label or the scoring records; the guard is in
code and exits rather than open them. An automated clean-room test rebuilds the pipeline in a
directory containing no oracle artefact and reproduces all eight outputs byte-identically.

**Scope, stated as scope and not as limitation.** The audit is deterministic by design and takes no
human input at any stage. It therefore does not assess substantive citation relevance, material
scope overreach beyond its frozen pattern, omitted limitations, or the adequacy of free-text
explanation. Those properties are out of scope. No independent reimplementation was produced, so
every figure rests on a single implementation; fixture agreement, canonicalisation tests and the
clean-room test constrain that implementation but do not establish independence from one
implementer's reading of the contracts.

**Results.** Reserved splits, 1,440 audited calls per model, 32 memory groups, normative scoped
reading. Development splits are reported in the reproducibility archive.

| Outcome | GPT-4.6 Terra | Qwen3 |
|---|---|---|
| Input–output trace reconstructibility, B0 / M0 / B1 | 99.6 / 98.8 / 99.8% | 97.9 / 98.5 / 96.3% |
| Cognitive-trace coherence, M0 / B1 | 100.0 / 100.0% | 100.0 / 98.8% |
| Critical-violation rate, worst condition | 0.00% | 0.21% |
| Trace-reconstructibility difference, B1 − B0 | +0.21 [+0.00, +0.62] | −1.67 [−3.75, +0.21] |
| Partial prospective field stability | 32 / 32 memories | 32 / 32 memories |

Intervals are paired memory-clustered bootstrap, 10,000 resamples. At 32 clusters, coverage is near
92.5% against a nominal 95%.

**Two critical violations, both traceable.** Of 4,800 audited cases, two carried a critical
violation, both from Qwen3 and both on the same memory (MEM51-0039): the returned rule could not
produce the returned reaction. One also failed the public response schema. Terra produced none in
2,400 cases.

**No supported condition difference, and a defect found in the making.** The first pass gave
−2.08 [−3.96, −0.21] for Qwen3, an interval excluding zero. A per-code sensitivity analysis run
before reporting found two defects in the source-attribution detector: a vocabulary entry that
never occurs as a source in the registry, and a character window that crossed clause boundaries.
Corrected, the estimate is −1.67 [−3.75, +0.21], which includes zero (paired permutation
p = 0.175). The point estimate remains negative and is reported as such, but no condition
difference is statistically supported for either model. The correction, its worked example and its
effect are recorded in the reproducibility archive.

**Interpretation.** The retained artefacts support reconstruction of the pathway in effectively
every condition. The Level 1 check set saturates by construction — the public
response schema has four fields and the frozen runner already rejects schema-invalid responses — so
the condition difference is reported as an instrument-integrity endpoint, not a discriminating one.
Protocol equation (7) is withdrawn from the confirmatory set: the release has no trace-writing path,
so a per-condition contrast of Level 2 would compare a dataset property that is invariant across all
five contexts, all three renderings and every model. Level 2 is therefore reported once for the
release as a release-integrity result.

**One finding that does discriminate.** Comparing the same canonical context across the
structured, chronological and concise renderings, Qwen3's cited evidence sets agreed exactly in
53.1% of B0 contexts against 33.1% of B1: a difference of −20.0 percentage points, 95% CI
[−31.25, −8.75], Holm-adjusted permutation p = 0.009, with B1 worse in 21 of 32 memories. The
effect is graded: the cited evidence destabilises most, the invoked rule next (−12.5 pp, Holm
p = 0.060), and the returned decision least (−8.1 pp, not distinguishable from zero). Terra shows
none of it — flat on all three measures, every interval spanning zero.

This contrast is **exploratory**: protocol section 14 declares cross-rendering consistency a
descriptive check, and quantifying it as a condition contrast is an addition rather than a
pre-specified endpoint. It should be reported as such. No response was unparseable and no
rendering group was incomplete, so no selection effect enters the comparison.

The reading it supports is narrow and worth stating precisely: giving one model a richer retained
memory made the *grounds it stated* less stable to how the same records were worded, while what it
decided was comparatively unaffected. That is a property of how a particular model consumes the
interface, not of cognitive memory as such, and decision accuracy alone could not have surfaced
it.

---

## What to apply, in order

1. Patch 1 — the guard sentence. Everything else depends on it.
2. Patch 2a and 2b — the two qualifiers.
3. Patch 3 — the main-paper statement, only once Supplementary Note N exists.
4. Patch 4 — the supplementary note.

## Open

The supplementary note references *Supplementary Note N*; the number depends on the current
supplement. Send the `.tex` and I will apply all four patches and fix the cross-references in one
pass.
