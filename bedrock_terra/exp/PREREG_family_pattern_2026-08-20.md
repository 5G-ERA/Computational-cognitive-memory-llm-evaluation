# Pre-registration: does item difficulty, not model weakness, predict where memory helps?

**Written 2026-08-20, BEFORE inspecting any family-level breakdown of the KIMI2 or Qwen3
reserved runs. Registered by Adrian, run operator. Exploratory and descriptive.**

## Origin of the hypothesis, stated plainly

The hypothesis was generated **post hoc** on the Terra reserved split, whose outcomes were read on
19 August 2026. There, all of Terra's error concentrated in the TEMPORAL_GAP template family
(15/16 of B0's errors; 10/10 on development), and B1 recovered ground precisely there.

Because it was generated after reading Terra, it is **not testable on Terra**. It is registered
here so it can be tested on data whose family-level breakdown has never been opened.

## Why the test set is clean

1. The KIMI2 and Qwen3 reserved family-level breakdowns have **never been computed or read** by
   the analyst, in any form.
2. What HAS been read on Qwen3 is accuracy by true outcome label. The v0.5.1 design is a complete
   crossing: **every (template_family x oracle_reaction) cell contains exactly 24 contexts**, so
   family and outcome are orthogonal by construction and the outcome-level view carries no
   information about the family-level view.
3. KIMI2 and Qwen3 reserved sets are disjoint from Terra in model, and identical in items.

## Hypotheses

- **H1 (difficulty is a property of the item).** In condition B0, TEMPORAL_GAP accuracy is lower
  than the mean accuracy of the other four families, in BOTH KIMI2 and Qwen3.
- **H2 (memory helps where difficulty is).** The B1-B0 benefit is larger in TEMPORAL_GAP than the
  mean B1-B0 benefit of the other four families, in BOTH KIMI2 and Qwen3.

## Pre-specified analysis

- Denominator: intention-to-evaluate, as frozen. Invalid replies count as incorrect.
- Scoring: the release's own parser and scorer, via `load_reserved` in the signed
  `analysis_section6.py` for KIMI2, and the same scorer's records for Qwen3. Nothing reimplemented.
- Statistic: accuracy by (family, condition); and the difference-in-differences
  `(B1-B0 | TEMPORAL_GAP) - (B1-B0 | other four families)`.
- Interval: the frozen memory-clustered bootstrap, 10,000 replicates, 95% percentile, seed 13082654,
  clustering on memory_id exactly as the primary analysis does.
- Reported for each model separately. **No pooling across models and no multiplicity adjustment**,
  because nothing here is a confirmatory claim.

## Decision rule, fixed in advance

- H1 holds if TEMPORAL_GAP has the lowest B0 accuracy of the five families in both models.
- H2 holds if the difference-in-differences point estimate is positive in both models.
- Anything else is reported as a failure to replicate, including partial replication.
- **The result is reported whatever it is.** This file is registered before the numbers exist.

## What this can and cannot become

It **cannot** become an endpoint, a subgroup claim, or evidence for the DCA. On 19 August the
decision owner ruled that arms may not be selected by measured headroom and that the same
objection applies at subgroup level; that ruling stands and this analysis does not touch it.

Its purpose is to characterise **the instrument**: if difficulty is a property of the item rather
than of the model, then a frontier model does not exhaust the benchmark, it narrows the region in
which the benchmark still discriminates. That is the answer to "the effect only appears in weak
models", and it is a statement about measurement, not about the hypothesis.

Any use of this in the paper requires the decision owner's own ruling.
