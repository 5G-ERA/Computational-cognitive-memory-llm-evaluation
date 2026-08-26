# Computational Cognitive Memory — LLM Evaluation

Release package for **Experiment 1 (LLM Multi-Model Evaluation)** of
*A Computational Theory of Cognitive Memory* (Qiu, Pham, Lendinez
Ibanez, Li — University of Bedfordshire / University of Birmingham,
draft V5.8, 2026-08): execution records, frozen benchmark releases,
analyses and QA reports for the medical assumption-memory benchmark
(v0.5.1 family) across three model arms.

The paper introduces **Computational Cognitive Memory (CCM)**: a
DCA-scoped cognitive interface (Decentralised Capability Abstraction —
Contextual Span, Semantic Locality, Authority Partitioning) plus
governed cognitive dynamics realised through **Distributed Cognitive
Continuity (DCC)**, with **E-DCA** (Experience-driven DCA) supplying the
evidence-resolved meta-level observation. Experiment 1 tests the local
formation-time observation and bounded meta-decision pathway across
multiple LLMs; it does not evaluate complete governed deployment.
(Experiment 2, the robotic development-to-deployment evaluation of
Supplementary Note 8, is **not** in this repository.)

**Start here:** [`EXPERIMENT1_RELEASE.md`](EXPERIMENT1_RELEASE.md) maps
this repository onto Supplementary Note 7 of the paper and populates its
manifest and results tables from the frozen records stored here.
Machine-readable results: [`results_table_v5_8.json`](results_table_v5_8.json).

## Conditions

All three conditions are built from the same source evidence and differ
only in the memory representation supplied; the LLM remains the final
local meta-decision maker.

| Paper term | Benchmark id | What the model receives |
|---|---|---|
| Raw longitudinal evidence | `B0_LLM_ALONE` | current + historical evidence, no explicit memory representation |
| Pre-specified consequence map | `M0_OPEN_LOOP_MEMORY` | prospective condition-to-consequence relation, evidence-supported consequence unresolved |
| Cognitive-memory representation | `B1_VERIFIED_MEMORY` | event-bound experiential contribution after formation-time meta-resolution through the DCA-scoped interface |

## Headline results (reserved / confirmatory split)

Primary contrast Δ_CM−Raw (= B1−B0), paired percentile bootstrap,
10,000 replicates clustered at the memory-group level, 32 memory
groups, 480 matched contexts, 1440 calls per model,
intention-to-evaluate.

| Arm (paper label) | Executed model | Δ_CM−Raw (pp) | 95% CI | Status |
|---|---|---|---|---|
| KIMI2 † | `kimi-dev-72b` (Q4_0) | **+9.79** | [+5.00, +14.79] | Confirmatory POSITIVE, sealed run, signed |
| Qwen3 | `qwen.qwen3-next-80b-a3b` (Bedrock) | **+25.21** | [+21.67, +28.54] | Confirmatory POSITIVE, pre-registered replication |
| GPT-4.6 Terra | `global.openai.gpt-5.6-terra` (Bedrock) | +1.04 | [−0.63, +2.92] | NOT ESTABLISHED — ceiling (Raw ≈ 96.7%); pre-registered family analysis: **+7.29 pp in TEMPORAL_GAP** |

† Paper label and executed checkpoint differ; see the reconciliation
note in `EXPERIMENT1_RELEASE.md`.

Declared caveats (full detail in the reports inside each directory):

- Qwen3 under Raw evidence collapses to `ESCALATE_REVIEW` (~89%); the
  benefit concentrates in non-escalate items. Δ_Map−Raw = −3.96 pp
  [−7.08, −0.83] (exploratory).
- Terra's null is an instrument ceiling, not evidence against the
  mechanism; its only margin — and its only benefit — is in the
  TEMPORAL_GAP family.
- With 32 memory clusters the bootstrap slightly undercovers (~92.5% vs
  nominal 95%); disclosed in the frozen release.
- The audit-extension findings (cross-rendering stability, replay
  recall, auditability without oracle) are **exploratory**, as declared
  in their reports. A replay-recall confirmatory test on the untouched
  Kimi arm is pre-registered but **has not been executed**
  (authorisation pending).

## Directory map (chronological)

| Directory | Content |
|---|---|
| `medical_assumption_memory_computational_benchmark_v0_5_1/` | Benchmark package v0.5.1 as received |
| `medical_assumption_memory_v0_5_1_qa1_patch/` | qa1 patch package and its review |
| `pkg_qa1b/` | qa1b implementation package (release-candidate work) |
| `release_qa1b/` | qa1b release candidate, incl. clean-room extract |
| `reserved_run_2026-08-15/` | **Kimi-arm reserved run**: 1440/1440 calls, raw + parsed responses, scoring records, freeze records, defect/restart decision logs |
| `patch_qa1c/` | Parser patch for DEFECT_001 (model emits `◁/think` without `▷`; 35 valid answers mis-scored) |
| `release_qa1c/` | Frozen release qa1c (dependency pins, freeze records) |
| `analysis/` | Section-6 analysis scripts and results |
| `bedrock_terra/` | **Terra and Qwen3 arms**: adapters, configs, dev + reserved runs, repeat runs, ablations, effort studies, coverage studies, analyses, HTML reports, authorisation/signature records, pre-registrations |
| `audit_extension/` | **Experiment-1 audit extension**: contracts, schemas, fixtures, deterministic validators, blind validator spec pack, results for dev/reserved splits of all three arms, exploratory reports |

Each subdirectory keeps its own `README.md` / reports where they
existed; internal paths in those documents refer to this same layout.

## Provenance and integrity

- Reserved splits were executed under sealed conditions; scoring and
  analysis were opened only after the corresponding authorisation
  records (see `bedrock_terra/signature/` and the freeze records in
  each release).
- Run manifests, SHA-256 freeze records and pre-registration hashes are
  included. Note the sanitization: a few files were edited *after*
  freezing to remove private infrastructure identifiers, so their bytes
  no longer match the recorded hashes — see `SANITIZATION.md` for the
  exact file list.
- Findings and defects are reported as found (e.g. `DEFECT_001`,
  `FINDING_002` addendum, `FINDING_003`), including the ones that were
  our own artefacts.
