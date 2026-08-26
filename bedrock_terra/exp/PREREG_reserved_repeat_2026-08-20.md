# Pre-registration: measuring run-to-run variability on the reserved split

**Written 2026-08-20, BEFORE launching the repeat run. Registered by Adrian, run operator.
Auxiliary measurement study. Not a confirmatory analysis and not a second attempt at a result.**

## Why this run exists

The frozen estimator is a memory-clustered bootstrap. It resamples MEMORIES, so it propagates
the uncertainty of having sampled these 32 memories rather than others. It does **not** propagate
a second, independent source: the model is stochastic (the endpoint accepts `seed` and does not
honour it), so each item carries exactly one realisation out of many possible ones.

Three development-split runs of Qwen3 executed on 19-20 August — two with the frozen
configuration and one with `reasoning_effort: medium`, a parameter the endpoint demonstrably
ignores — behave as three replicates of the same experiment. They give
**sd(B1-B0) ~ 3.0 pp on 120 contexts**, with M0 the least stable condition (sd ~ 3.5 pp).

Extrapolated to the reserved split and combined in quadrature with the published intervals, that
would leave the primary claim intact but would push **both** M0-B0 intervals back across zero.
That extrapolation rests on three replicates and a 1/sqrt(n) scaling. It is not evidence. It is a
reason to measure the quantity directly, at the sample size that matters.

## The binding condition, fixed before the data exist

1. **The original reserved run `out/reserved_qwen3` remains the sole basis of every published
   estimate.** It is not superseded, replaced, averaged, or pooled with the repeat.
2. **The repeat may not be used to revise, improve, or restate any published number.** If it
   returns a larger effect, that is not reported as a better result. If it returns a smaller one,
   the published estimate still stands as published.
3. The repeat's only sanctioned use is estimating run-to-run variance and reporting it as a
   declared limitation.
4. Having two runs must not become a choice between two runs. This clause exists because that is
   exactly the defect the project has spent its whole history avoiding.

## Pre-specified analysis

- Execute the reserved split with the frozen `config/model_qwen3_bedrock.json`, unchanged, into
  `out/reserved_qwen3_repeat`. Same runner, scorer, seed, order.
- Report, for each of the three contrasts, the value in run 1, the value in run 2, and their
  difference.
- Estimate run-to-run sd from the two reserved runs directly, with no scaling from development.
- Recompute each published interval with the two sources combined in quadrature, and report it
  **as a sensitivity analysis alongside the frozen interval, never in place of it.** The frozen
  estimator is not modified.

## Decision rule, fixed in advance

- If the primary B1-B0 interval still excludes zero once run-to-run variance is propagated, the
  primary claim is reported unchanged, with the sensitivity disclosed.
- **If either M0-B0 interval no longer excludes zero, M0-B0 is demoted to a direction** in every
  document that currently reports it as an interval excluding zero, and the demotion is stated
  explicitly rather than quietly dropped. That includes the Cross-Model Replication Result page,
  which currently headlines it.
- The result is reported whatever it is.

## What this cannot become

Not an endpoint, not a claim, not a replacement dataset. The confirmatory result of 19 August
stands on the original run. This measures how much that number would move if the same model were
asked the same questions again, which is a property of the instrument that the paper must
disclose and currently does not.
