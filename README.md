<h1 align="center">Computational Cognitive Memory<br/>LLM Evaluation</h1>

<p align="center">
  <a href="https://github.com/5G-ERA/Computational-cognitive-memory-llm-evaluation/actions/workflows/verify.yml"><img alt="verify" src="https://github.com/5G-ERA/Computational-cognitive-memory-llm-evaluation/actions/workflows/verify.yml/badge.svg"></a>
  <img alt="Reproduction: offline" src="https://img.shields.io/badge/reproduction-offline%2C%20no%20model%20calls-2ea44f">
  <img alt="Python" src="https://img.shields.io/badge/python-%E2%89%A5%203.8%20%2B%20numpy-blue">
  <img alt="Models" src="https://img.shields.io/badge/arms-Kimi%20%C2%B7%20Qwen3%20%C2%B7%20GPT--Terra-8a2be2">
</p>

<p align="center">
  <em>Results and reproducibility package for Experiment 1 of<br/>
  <strong>A Computational Theory of Cognitive Memory</strong><br/>
  Qiu · Pham · Lendinez Ibanez · Li — University of Bedfordshire · University of Birmingham (draft V8.55, November 2026)</em>
</p>

---

The paper introduces **Computational Cognitive Memory (CCM)**: a
DCA-scoped cognitive interface plus governed cognitive dynamics
realised through Distributed Cognitive Continuity (DCC). **Experiment 1**
asks whether an evidence-resolved cognitive-memory representation
improves an LLM's meta-decision over raw longitudinal evidence and over
a pre-specified consequence map built from the same source material.
This repository holds the frozen benchmark releases, execution records,
analyses and QA reports of that experiment, and reproduces every
reported number offline.

**Experiment 2**, the robotic evaluation (embodiment transfer across
Summit XL simulation, physical Summit XL and Unitree G1), is in
progress. Its full scope, the three conditions (C2, C2.5, C3) and the
current state of the evidence are in
[`EXPERIMENT2_SCOPE.md`](EXPERIMENT2_SCOPE.md). No Experiment 2 result is
claimed yet, and its records are not in this repository.

## Results

The two tables below are Tables 3 and 4 of the paper (draft V8.55).

Reserved (confirmatory) split — 32 memory groups, 480 matched contexts,
1440 calls per model, intention-to-evaluate denominator, percentile
bootstrap with 10,000 replicates clustered at the memory-group level.

Conditions, with the paper's names and the benchmark identifiers:
**Raw Evidence (B0)** = `B0_LLM_ALONE` · **Consequence Map (M0)** =
`M0_OPEN_LOOP_MEMORY` · **Evidence-Resolved CCM (B1)** =
`B1_VERIFIED_MEMORY`. The pre-specified primary contrast is **B1 − B0**;
**B1 − M0** evaluates improvement beyond consequence preservation.

### Response accuracy (paper Table 3)

| Model arm | Executed model | B0 | M0 | B1 | **B1 − B0** | B1 − M0 |
|---|---|--:|--:|--:|---|---|
| KIMI2 [^1] | `kimi-dev-72b` (Q4_0) | 74.17% | 70.42% | 83.96% | **+9.79 pp**, 95% CI [+5.00, +14.79] | +13.54 pp, secondary contrast |
| Qwen3 | `qwen.qwen3-next-80b-a3b` | 29.38% | 25.42% | 54.58% | **+25.21 pp**, 95% CI [+21.67, +28.54] | +29.17 pp, 95% CI [+25.42, +32.92] |
| GPT-5.6 Terra | `global.openai.gpt-5.6-terra` | 96.67% | 95.21% | 97.71% | +1.04 pp, 95% CI [−0.63, +2.92]; not established: ceiling | +2.50 pp, descriptive contrast |

KIMI2 is the sealed, signed confirmatory run; Qwen3 is the
pre-registered replication; the GPT-5.6 Terra arm is at the ceiling of
the instrument, so its primary contrast is not established and its
B1 − M0 difference is descriptive only (it was gated on the primary).

The benefit requires *resolving what the evidence supported*, not
merely exposing the expected consequence relation, whose own effect is
null or negative (M0 − B0: −3.96 pp [−7.08, −0.83] in Qwen3,
exploratory).

**Pre-registered family analysis** (secondary): the effect concentrates
in the **TEMPORAL_GAP** family — +28.12 pp (KIMI2), +29.17 pp
(Qwen3) and **+7.29 pp for GPT-5.6 Terra**, whose only margin below
ceiling is exactly there (`bedrock_terra/exp/exp1_family_pattern.json`).

Machine-readable outcomes: [`results_table_v5_8.json`](results_table_v5_8.json) ·
Release mapping: [`EXPERIMENT1_RELEASE.md`](EXPERIMENT1_RELEASE.md)
(written against the Supplementary Note numbering of draft V5.8).

> **Declared caveats.** Qwen3 under B0 collapses to `ESCALATE_REVIEW`
> (~89%), so its benefit concentrates in non-escalate items. The GPT-5.6
> Terra null is a ceiling of the instrument, not evidence against the
> mechanism. With 32 clusters the bootstrap undercovers (~92.5% vs
> nominal 95%), disclosed at freeze.

[^1]: The paper label and the executed checkpoint differ; see the
    reconciliation note in `EXPERIMENT1_RELEASE.md`.

## Reconstruction and replay

### Invariant-replay reconstruction (paper Table 4)

Each context has three differently worded renderings. Invariant-replay
recall is the share of contexts containing an error in which the error
is made visible by rule disagreement across the three renderings. The
detector needs no oracle and has 100% precision by construction. It
measures recovery of the governing relational invariant, not only the
selected response.

Reserved split. Intervals are memory-clustered bootstrap, 10,000
resamples.

| Model arm | B0 | M0 | B1 | **B1 − B0** | B1 − M0 |
|---|--:|--:|--:|---|---|
| KIMI2 | 65.9% (29/44) | 83.0% (44/53) | 96.4% (27/28) | **+29.63 pp**, 95% CI [+8.81, +51.28]; permutation p = 0.021, 24 clusters | +14.07 pp, 95% CI [+0.17, +27.27]; permutation p = 0.078, 24 clusters |
| Qwen3 | 30.4% (38/125) | 15.7% (20/127) | 60.2% (56/93) | **+29.82 pp**, 95% CI [+17.14, +42.23]; permutation p < 0.001, 32 clusters | +44.47 pp, 95% CI [+34.02, +54.86]; permutation p < 0.001, 32 clusters |
| GPT-5.6 Terra | 77.8% (7/9) | 72.7% (8/11) | 100.0% (7/7) | not estimated: 9 / 11 / 7 contexts with an error | not estimated |

**Why a contrast is not the difference of the two displayed
percentages.** For KIMI2, 96.4 − 65.9 = 30.5, while the reported
contrast is 29.63. Both are correct. The displayed percentage of a
condition pools every erroneous context of that condition (44 under B0,
28 under B1). The contrast is *paired by memory group*: it uses only the
memory groups that have at least one erroneous context under both
conditions (24 of 32 for KIMI2), pools within those groups and takes the
difference; the interval is the bootstrap over the same groups. This is
the pre-registered estimator
(`audit_extension/scripts/calculate_clustered_intervals.py`).

**Discovery and pre-registered confirmation.** The replay result follows
a discovery–confirmation design, and the confirmation succeeded.

- **Discovery (Qwen3).** The effect was first observed on Qwen3:
  B1 − B0 = +29.82 pp, 95% CI [+17.14, +42.23]. GPT-5.6 Terra made too
  few errors to estimate it (five memory groups with an error under both
  conditions).
- **Confirmation (KIMI2).** The hypothesis was then pre-registered on
  22 August 2026 for the KIMI2 reserved arm, before any replay quantity
  had been computed on it: endpoint, detector, estimator, seed and
  success criterion (a 95% interval excluding zero with a positive
  estimate; the permutation test as a robustness check). The test was
  run once, on 8 November 2026, under that frozen protocol, with the
  input and interval-code hashes matching the pinned values. Result:
  B1 − B0 = +29.63 pp, 95% CI [+8.81, +51.28], permutation p = 0.021.
  **The success criterion is met**, and the effect on an independent
  model has almost the same size as on the discovery arm.
- **B1 − M0 (beyond consequence preservation).** This secondary contrast
  was added on 23 November 2026, with the same estimator, so that this
  table reports the same two contrasts as the response-accuracy table.
  It was not part of the pre-registration. Under the same criterion, the
  interval excludes zero with a positive estimate in both arms: KIMI2
  +14.07 pp [+0.17, +27.27] and Qwen3 +44.47 pp [+34.02, +54.86]. The
  permutation robustness check gives p = 0.078 for KIMI2 and p < 0.001
  for Qwen3.

All four estimated contrasts, and the counts in the table, re-derive
offline from the frozen scoring records:

```bash
python3 audit_extension/scripts/replay_recall_contrasts.py
```

Output: `audit_extension/results/join/replay_recall_contrasts.json`.
The script re-derives the KIMI2 B1 − B0 result and stops if it does not
match the sealed confirmatory record.

**Artefacts of the KIMI2 confirmatory test.**

| Artefact | Path |
|---|---|
| Pre-registration (endpoint, detector, seed, pinned input and code hashes, criterion) | `audit_extension/validation/PREREG_replay_recall_kimi_2026-08-22.json` |
| Execution authorisation | `audit_extension/validation/AUTHORISATION_reserved_audit_002.json` |
| Scoring input (qa1c parse of the 1440 sealed captures) | `audit_extension/results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl` |
| Runner | `audit_extension/scripts/run_confirmatory_replay.py` |
| Final result, with the hashes of the prereg, authorisation, input and code it ran under | `audit_extension/results/kimi_confirmatory/CONFIRMATORY_RESULT.json` |

The four hashes recorded in the result match the published files. The
runner refuses a second confirmatory run. Contexts with fewer than three
valid renderings were dropped as pre-specified: 17 / 22 / 13.

**How the KIMI2 records were signed.** The prereg and
`AUTHORISATION_reserved_audit_002.json` ask for Renxi Qiu's direct
signature. Both were signed as **DELEGATED**, by Adrian Lendinez Ibanez on
Renxi Qiu's behalf, on 8 November 2026, before the test ran. Each record
says so (`satisfies_signature_requirement_literally: false`, with its
caveat). Signing changed only the signature fields, and `runs_authorised`
in the authorisation.

**Other audit-extension endpoints.** The audit extension also computed
trace reconstructibility, trace coherence, identical-replay recall and
an audit index. They are exploratory, they are not reported in the
paper, and they are no longer summarised here. Their outputs remain in
[`audit_extension/`](audit_extension/) (`results/reserved_{kimi,qwen3,terra}/`
and `results/join/`). All audit-extension figures rest on a single
implementation: the independent-reimplementation requirement was removed
for Experiment 1 by decision E1-G1. They are not the endpoints of
Experiment 2.

## Reproduce the results

Offline, from the frozen records in this repository — no model calls,
no network. Requires Python ≥ 3.8 and numpy. The
[`verify` workflow](.github/workflows/verify.yml) runs this same check
on every push.

```bash
python3 reproduce/verify_experiment1.py
```

```
== terra: re-derived from raw captures. CM-Raw +1.0417 pp, CI95 [-0.6250, 2.9167] OK
== qwen3: re-derived from raw captures. CM-Raw +25.2083 pp, CI95 [21.6667, 28.5417] OK
== kimi arm (kimi-dev-72b): recomputed from qa1c-scored records. CM-Raw +9.7917 pp OK

All three arms reproduce the frozen results, including the
bootstrap intervals of the Bedrock arms (deterministic seed).
```

The verifier re-derives the Terra and Qwen3 reserved results from the
**raw terminal captures** through the frozen pipeline (parse → scoring →
frozen clustered bootstrap, deterministic seed) and checks accuracies,
contrasts *and intervals* against the frozen outputs; the Kimi arm is
recomputed from the qa1c-scored records of its sealed confirmatory run.

➡ [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) — pipeline map, seeds,
seals and authorisation records, the scoring rule (and a trap to
avoid), integrity hashes, and what cannot be reproduced from here.

## Repository layout

Ordered by function. Internal paths in the frozen reports refer to this
same layout, so directories are not renamed.

#### Results and analysis

| Path | Content |
|---|---|
| [`results_table_v5_8.json`](results_table_v5_8.json) | Machine-readable multi-model outcomes |
| `bedrock_terra/out/analysis_reserved_*.json` | Frozen confirmatory analyses (Terra, Qwen3) |
| `audit_extension/results/kimi_confirmatory/` | qa1c-scored records of the sealed Kimi-arm run |
| `audit_extension/results/join/replay_recall_contrasts.json` | Invariant-replay recall, B1 − B0 and B1 − M0 for the three arms (paper Table 4) |
| `bedrock_terra/exp/` | Pre-registered family/repeat analyses + SHA-256 preregs |
| `analysis/` | Signed frozen estimator (`analysis_section6.py`) and section-6 outputs |
| `bedrock_terra/EDCA_*.html` | Execution, eligibility, results and instrument reports |

#### Reproduction

| Path | Content |
|---|---|
| [`reproduce/verify_experiment1.py`](reproduce/verify_experiment1.py) | One-command offline verification of all three arms |
| [`reproduce/run_frozen_analysis.py`](reproduce/run_frozen_analysis.py) | Runs the frozen pipeline on a preserved run directory |
| `bedrock_terra/analysis_dev_arm.py` | Frozen analysis entry point (seal-enforcing) |
| `bedrock_terra/signature/` | Signed authorisation/inspection records that release the seals |

#### Frozen benchmark and execution records

| Path | Content |
|---|---|
| `release_qa1c/` | Frozen benchmark release qa1c (prompts, oracle, freeze records, pins) |
| `reserved_run_2026-08-15/` | Kimi-arm reserved run: 1440/1440 raw captures, manifests, defect logs |
| `bedrock_terra/out/reserved_*/` | Terra and Qwen3 reserved runs: raw captures, manifests, completion reports |
| `bedrock_terra/config/` · `bedrock_terra/adapters/` | Frozen model configs and transport adapters |

#### History and QA (how the release got here)

| Path | Content |
|---|---|
| `medical_assumption_memory_computational_benchmark_v0_5_1/` | Benchmark v0.5.1 as received |
| `medical_assumption_memory_v0_5_1_qa1_patch/` · `pkg_qa1b/` · `release_qa1b/` | qa1 review and qa1b release-candidate work |
| `patch_qa1c/` | Parser fix for DEFECT_001 (35 valid answers mis-scored) |
| `audit_extension/` | Experiment-1 audit extension: contracts, validators, exploratory results |

## Provenance and integrity

- Reserved splits were executed **sealed**; scoring and analysis opened
  only under the signed authorisation records in
  `bedrock_terra/signature/` — the analysis tooling refuses to run
  without them, by code.
- Run manifests, SHA-256 freeze records, prereg hashes and dependency
  pins are included. 28 files had private infrastructure identifiers
  redacted *after* freeze for publication ([`SANITIZATION.md`](SANITIZATION.md)),
  so the bytes of those specific files no longer match the recorded
  hashes.
- Defects found along the way are reported as found (`DEFECT_001`,
  `FINDING_002` addendum, `FINDING_003`), including the ones that were
  our own artefacts.

## Citation

See [`CITATION.cff`](CITATION.cff). Please cite the paper:

> R. Qiu, D. Pham, A. Lendinez Ibanez, D. Li. *A Computational Theory
> of Cognitive Memory.* Draft V8.55, November 2026. Manuscript in
> preparation.
