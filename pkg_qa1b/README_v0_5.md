# Medical Assumption Memory Computational Benchmark v0.5

v0.5 is the semantic robustness and control-condition development release built on the v0.4.2 API-ready system.

## Additions

- 200 balanced canonical hidden contexts, 40 per reaction
- three independent rendering families per context
- 600 rendered contexts and 1,800 B0/M0/B1 calls
- 40 development and 160 reserved canonical contexts, stratified by reaction
- relational successor evidence rather than direct successor-state labels
- outcome-only, sham-memory, and token-matched M0 development controls
- rendering-family and counterfactual identity maps
- inherited deterministic API runner, response interpreter, evidence scorer, KPI tools, and external API QA framework

## Important status

This package is for generator validation and v0.5 development. Do not execute the reserved set until challenge baselines, rendering fidelity, paraphrase equivalence, external API QA, and release-freeze gates pass.
