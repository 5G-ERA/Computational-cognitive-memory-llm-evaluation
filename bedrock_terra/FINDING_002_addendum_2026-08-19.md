# Addendum to Finding 002 — coverage of the frozen section 6 estimator

**Date:** 19 August 2026.
**Status of the original finding: CONFIRMED, not weakened.** No change to the disclosure
already published with the sealed KIMI2 reserved result.
**Estimator altered:** no.
**Reserved outcomes inspected:** none. Run before any reserved contrast was opened.

---

## Why this was revisited

Finding 002 rested on a single scenario inside the estimator's own self-test: 400 replicates
at one baseline. The number it produced — about 92.5% coverage, criterion firing at about
4.0% — goes into the paper as a stated limitation. A figure that a reviewer may quote deserves
more than one cell, so it was measured across a grid before the Qwen3 reserved split was
opened, when no result could influence how it was reported.

## Result: the original figure reproduces

At the scenario the original used — 32 memory clusters, baseline 0.55, true null, memory-by-
condition interaction present — an independent grid of 1,000 replicates × 2,000 bootstrap
resamples gives:

| Source | Coverage | Criterion fires under the null |
| --- | --- | --- |
| Finding 002, as published | 92.5% | 4.0% |
| This addendum, same scenario | **92.8%** | **4.1%** |

The published disclosure is accurate. It is neither too harsh nor too generous.

## What the grid adds

**Coverage depends on the baseline, and the dependence is mild in the range that matters.**
With 32 clusters under a true null: 94.4% at baseline 0.33, 92.8% at 0.55, 92.0% at 0.75.
The criterion fires at 2.7%, 4.1% and 1.4% respectively. Reporting a single number is
therefore a simplification, and 92.5% is a fair representative of the middle of the range.

**With 8 clusters the estimator is materially worse: coverage about 89.6% and the criterion
fires at about 5.1%, twice its nominal 2.5%.** This does not affect any reserved result — the
reserved split has 32 memories — but it does apply to development-split contrasts, which
should not be quoted with a 95% interval as though it were one.

## Two corrections to intermediate work, recorded rather than quietly dropped

**A high-baseline collapse was observed and is withdrawn as a simulation artefact.** A first
pass reported coverage falling to 57.2% at baseline 0.75 with an 18 pp effect. The cause was
the clip at p = 0.99: at that baseline the nominal effect is never realised — a nominal 18 pp
produces a realised 12.5 pp, and a nominal 10 pp produces 7.0 pp — so those cells measured
whether the interval covered a value the simulation had not generated. It is not a property
of the estimator and must not be reported as one.

**Re-measuring against the realised estimand over-corrects, and the difference is a question
of estimand rather than of arithmetic.** Taking the truth to be the realised probability-level
difference for the specific memories drawn gives coverage of 98.4% at the same scenario: the
interval becomes conservative. That is the *conditional*, finite-population estimand — the
effect on these 32 memories. The clustered bootstrap resamples whole memories precisely
because it targets the *superpopulation* estimand: the effect over memories of this kind,
which is what generalisation beyond the reserved 32 requires, and what the paper claims. Under
that reading, 92.5% stands.

Worth stating in the annex, because a reviewer may raise it: the reserved split is a fixed
enumerated set, so a finite-population reading is defensible and would make the interval
conservative rather than anticonservative. The published claim uses the superpopulation
reading, which is the stricter of the two.

## What follows

- **No change to Finding 002.** The disclosure as published is correct for the estimand claimed.
- **Do not weaken it.** An earlier internal note in this session suggested the limitation was
  milder than declared. That came from averaging coverage across baselines, including one where
  the estimator does better, and was wrong.
- **Development-split contrasts carry a different figure.** Any development number quoted
  externally should carry the 8-cluster characteristic (~89.6% coverage, criterion firing at
  ~5.1%), not the 32-cluster one.
- A BCa or cluster-t interval would improve coverage at this cluster count. That remains a
  future-release decision, to be taken before results are seen.

## Reproduce

```bash
cd ~/dca_v051/bedrock_terra
python3 coverage_study.py --reps 1000 --boot 2000 --out out/coverage_study.json      # superpopulation truth
python3 coverage_study_v2.py                                                          # conditional truth
```

Both import the estimator from the signed `analysis_section6.py` and alter nothing in it.
Neither reads any run data: they are simulation against a known truth.
