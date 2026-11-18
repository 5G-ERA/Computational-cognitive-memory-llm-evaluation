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
  Qiu · Pham · Lendinez Ibanez · Li — University of Bedfordshire · University of Birmingham (draft V5.8, 2026-08)</em>
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

Reserved (confirmatory) split — 32 memory groups, 480 matched contexts,
1440 calls per model, intention-to-evaluate denominator, percentile
bootstrap with 10,000 replicates clustered at the memory-group level.

Conditions: **Raw** = `B0_LLM_ALONE` · **Map** = `M0_OPEN_LOOP_MEMORY` ·
**CM** = `B1_VERIFIED_MEMORY`. Primary contrast **Δ = CM − Raw**.

| Arm (paper label) | Executed model | Raw | Map | CM | **Δ CM−Raw** | 95% CI | Status |
|---|---|--:|--:|--:|--:|:-:|---|
| KIMI2 [^1] | `kimi-dev-72b` (Q4_0) | 74.17% | 70.42% | 83.96% | **+9.79 pp** | [+5.00, +14.79] | ✅ POSITIVE — sealed run, signed |
| Qwen3 | `qwen.qwen3-next-80b-a3b` | 29.38% | 25.42% | 54.58% | **+25.21 pp** | [+21.67, +28.54] | ✅ POSITIVE — pre-registered replication |
| GPT-4.6 Terra | `global.openai.gpt-5.6-terra` | 96.67% | 95.21% | 97.71% | +1.04 pp | [−0.63, +2.92] | ⬜ NOT ESTABLISHED — instrument ceiling |

**Key secondary** (CM − Map, gated on the primary): +13.54 pp (Kimi
arm), +29.17 pp [+25.42, +32.92] (Qwen3). The benefit requires
*resolving what the evidence supported*, not merely exposing the
expected consequence relation, whose own effect is null or negative
(Map − Raw: −3.96 pp [−7.08, −0.83] in Qwen3, exploratory).

**Pre-registered family analysis** (secondary): the effect concentrates
in the **TEMPORAL_GAP** family — +28.12 pp (Kimi arm), +29.17 pp
(Qwen3) and **+7.29 pp for Terra**, whose only margin below ceiling is
exactly there (`bedrock_terra/exp/exp1_family_pattern.json`).

Machine-readable outcomes: [`results_table_v5_8.json`](results_table_v5_8.json) ·
Paper mapping (Supp. Note 7 tables): [`EXPERIMENT1_RELEASE.md`](EXPERIMENT1_RELEASE.md)

> **Declared caveats.** Qwen3 under Raw collapses to `ESCALATE_REVIEW`
> (~89%), so its benefit concentrates in non-escalate items. Terra's
> null is a ceiling of the instrument, not evidence against the
> mechanism. With 32 clusters the bootstrap undercovers (~92.5% vs
> nominal 95%), disclosed at freeze.
>
> **Audit extension.** The pre-registered invariant-replay recall
> analysis was executed on the untouched Kimi reserved arm under the
> frozen protocol, once, on 8 November 2026. It is complete: B1−B0
> +29.63 pp [+8.81, +51.28], success criterion met. The result, interval,
> execution authorisation and verification artefacts are listed in
> [Reconstruction and replay](#reconstruction-and-replay). The other
> audit-extension endpoints are exploratory.

[^1]: The paper label and the executed checkpoint differ; see the
    reconciliation note in `EXPERIMENT1_RELEASE.md`.

## Reconstruction and replay

The table above is decision performance. Experiment 1 also has an
oracle-independent audit of the retained artefacts, implemented in
[`audit_extension/`](audit_extension/) (protocol of 22 August 2026,
retrospective, no new model calls). It asks a different question:
whether the pathway from visible evidence to output can be
reconstructed from the record and replayed. A trace can be
reconstructible while the decision is wrong, and the reverse.

Reserved split, 480 expected calls per condition, SCOPED reading
(normative; LITERAL is a declared sensitivity in the same files).
Intervals are memory-clustered bootstrap, 10,000 resamples, 32 clusters
unless stated.

| Endpoint | Arm | Raw | Map | CM | Contrast |
|---|---|--:|--:|--:|--|
| Input-output trace reconstructibility (Level 1) | KIMI2 | 74.58% | 79.38% | 78.33% | CM−Raw +3.75 pp [−1.46, +8.75] |
| | Qwen3 | 97.92% | 98.54% | 96.25% | CM−Raw −1.67 pp [−3.75, +0.21] |
| | GPT-4.6 Terra | 99.58% | 98.75% | 99.79% | CM−Raw +0.21 pp [0.00, +0.62] |
| Cognitive-trace coherence (Level 2) | KIMI2 | n/a by design | 100.00% | 84.79% | CM−Map −15.21 pp [−18.33, −12.08] |
| | Qwen3 | n/a by design | 100.00% | 98.75% | CM−Map −1.25 pp [−2.29, −0.42] |
| | GPT-4.6 Terra | n/a by design | 100.00% | 100.00% | CM−Map 0.00 pp |
| Invariant-replay recall: errors made visible by rule disagreement across the three renderings of a context | **KIMI2, confirmatory** | 65.9% | 83.0% | 96.4% | **CM−Raw +29.63 pp [+8.81, +51.28]**, permutation p = 0.021, 24 clusters |
| | Qwen3 | 30.4% | 15.7% | 60.2% | CM−Raw +29.82 pp [+17.14, +42.23] |
| | GPT-4.6 Terra | 77.8% | 72.7% | 100.0% | not estimated: 9 / 11 / 7 contexts with an error |
| Identical-replay recall: the same call repeated | Qwen3 | 16.1% | 9.6% | 37.0% | not estimated (no repeat run for KIMI2 or Terra) |
| Q_audit, Eq. (37) of draft V4.7, ×100 | KIMI2 | 87.92 | 81.61 | 87.70 | CM−Raw −0.22 [−4.35, +4.02] |
| | Qwen3 | 89.03 | 93.46 | 81.10 | CM−Raw −7.93 [−12.37, −3.59] |
| | GPT-4.6 Terra | 95.33 | 95.04 | 95.33 | CM−Raw +0.01 [−1.52, +1.54] |

How to read it:

- **For Qwen3 and Terra, Level 1 sits at a ceiling by construction** (a
  four-field response schema, and the executor already rejects invalid
  output). It is an instrument-integrity endpoint and certifies form, not
  correctness: 330 of the 470 conformant Qwen3 Raw traces carry a wrong
  decision (`audit_extension/results/join/reserved_qwen3.json`).
- **KIMI2 is not at that ceiling.** About one trace in four is not
  reconstructible: 122 / 99 / 104 of 480. The largest cause is a trace
  that does not name the current or the historical grounds of its decision
  (`E1_CURRENT_GROUNDS_MISSING` and `E1_HISTORICAL_GROUNDS_MISSING`,
  83 / 60 / 73). The rest are truncated outputs (18 / 24 / 16), outputs
  that fail the audit schema (16 / 9 / 10) and source misattribution
  (5 / 6 / 5), counted by primary code in
  `audit_extension/results/reserved_kimi/audit_root_causes.csv`. Its
  Level 2 coherence under CM is 84.79%.
- **The information is in replay.** The replay detector needs no oracle
  and has 100% precision by construction. Under CM, Qwen3 makes about
  twice as many of its errors visible, in both replay forms.
- **Q_audit falls under CM in Qwen3 because errors become visible.** The
  fall concentrates on erroneous boundaries (−16.17 [−22.05, −10.30])
  against −1.23 [−2.68, −0.36] on correct ones: CM errors become
  inconsistent across renderings instead of consistently wrong.
- **The KIMI2 replay test is confirmatory and complete.** The hypothesis
  was formed on Qwen3 and Terra, then pre-registered on 22 August 2026,
  before any audit or replay quantity was computed on KIMI2. It was run
  once, on 8 November 2026, under that frozen protocol. The input and
  interval-code hashes matched the pinned values, and the success
  criterion (a 95% interval excluding zero with a positive estimate) is
  met. The artefacts:

  | Artefact | Path |
  |---|---|
  | Pre-registration (endpoint, detector, seed, pinned input and code hashes, criterion) | `audit_extension/validation/PREREG_replay_recall_kimi_2026-08-22.json` |
  | Execution authorisation | `audit_extension/validation/AUTHORISATION_reserved_audit_002.json` |
  | Scoring input (qa1c parse of the 1440 sealed captures) | `audit_extension/results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl` |
  | Runner | `audit_extension/scripts/run_confirmatory_replay.py` |
  | Final result, with the hashes of the prereg, authorisation, input and code it ran under | `audit_extension/results/kimi_confirmatory/CONFIRMATORY_RESULT.json` |

  The four hashes recorded in the result match the published files. The
  result re-derives offline:
  `python3 audit_extension/scripts/run_confirmatory_replay.py --dry-run-on audit_extension/results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl`
  reproduces every endpoint field. The runner refuses a second
  confirmatory run. The paired contrast
  uses the 24 memories with at least one erroneous context under both
  conditions. Contexts with fewer than three valid renderings were dropped
  as pre-specified: 17 / 22 / 13. Secondary endpoints, descriptive: rule
  consistency CM−Raw was predicted negative and came out +1.91 pp
  [−5.40, +9.60], not as predicted. Citation stability among all-correct
  minus with-error contexts was predicted to flip from negative to
  positive, and did: −9.34 under Raw, +7.98 under CM.
- **How the KIMI2 records were signed.** The prereg and
  `AUTHORISATION_reserved_audit_002.json` ask for Renxi Qiu's direct
  signature. Both were signed as **DELEGATED**, by Adrian Lendinez Ibanez on
  Renxi Qiu's behalf, on 8 November 2026, before the test ran. Each record
  says so (`satisfies_signature_requirement_literally: false`, with its
  caveat). Signing changed only the signature fields, and `runs_authorised`
  in the authorisation.
- **The other KIMI2 rows are exploratory.** Levels 1–2 and Eq. (37) were
  computed after the confirmatory result, with the frozen pipeline and
  without the oracle. They ran in an environment (Python 3.10.12, PyYAML
  5.4.1, numpy 1.21.5) that first reproduced the frozen Qwen3 reserved
  audit byte for byte (seven outputs) and its Eq. (37). The join with
  decision accuracy has not been computed for KIMI2.
- **Status.** Apart from the KIMI2 replay test, every figure here is
  exploratory post hoc. All of them rest on a single implementation: the
  independent-reimplementation requirement was removed for Experiment 1 by
  decision E1-G1. The bootstrap undercovers as in the decision results.
- These are the audit extension's endpoints. They are not the
  certificate-recovery endpoint of Experiment 2.

Sources: `audit_extension/results/reserved_{kimi,qwen3,terra}/audit_report.md`,
`audit_condition_metrics.csv` and `audit_contrasts.json`;
`audit_extension/results/kimi_confirmatory/CONFIRMATORY_RESULT.json`;
`audit_extension/results/join/auditability_reserved_*.json` and
`eq37_reserved_*.json`.

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
> of Cognitive Memory.* Draft V5.8, August 2026. Manuscript in
> preparation.
