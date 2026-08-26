# Computational Cognitive Memory — LLM Evaluation

Evaluation materials, execution records and results for the computational
cognitive-memory benchmark (medical assumption-memory task, v0.5.1 family),
run across three model arms: **Kimi-Dev-72B** (private endpoint),
**GPT-5.6 "Terra"** (AWS Bedrock) and **Qwen3-Next-80B-A3B** (AWS Bedrock).

Work carried out within the 5G-ERA collaboration (University of Bedfordshire),
2026-08. Benchmark design and protocol: Renxi Qiu. Execution, QA and
analysis: Adrian Lendinez, assisted by Claude Code.

## Headline results (reserved / confirmatory splits)

Primary contrast: **B1 (verified cognitive memory) − B0 (LLM alone)**,
paired bootstrap, 10,000 replicates, 1440 calls per arm.

| Arm | Model | B1−B0 (pp) | 95% CI | Status |
|---|---|---|---|---|
| Kimi | Kimi-Dev-72B | **+9.79** | [+5.00, +14.79] | Confirmatory, sealed run, signed |
| Qwen3 | qwen3-next-80b-a3b (Bedrock) | **+25.21** | [+21.67, +28.54] | Confirmatory, pre-registered replication |
| Terra | gpt-5.6-terra (Bedrock) | +1.04 | [−0.63, +2.92] | Ceiling effect (B0 ≈ 96.7%): instrument does not discriminate |

Declared caveats (see the reports inside each directory for full detail):

- Qwen3 in B0 collapses to `ESCALATE_REVIEW` (~89%); the benefit is
  concentrated in the non-escalate items. Secondary contrast
  M0−B0 = −3.96 pp [−7.08, −0.83].
- Terra's null is a ceiling effect of the instrument, not evidence against
  the mechanism.
- With 32 memory clusters the bootstrap slightly undercovers (~92.5% vs
  nominal 95%); disclosed in the frozen release.
- The audit-extension findings (cross-rendering stability, replay recall,
  auditability without oracle) are **exploratory**, as declared in their
  reports. A replay-recall confirmatory test on the untouched Kimi arm is
  pre-registered but **has not been executed** (authorisation pending).

## Directory map (chronological)

| Directory | Content |
|---|---|
| `medical_assumption_memory_computational_benchmark_v0_5_1/` | Benchmark package v0.5.1 as received |
| `medical_assumption_memory_v0_5_1_qa1_patch/` | qa1 patch package and its review |
| `pkg_qa1b/` | qa1b implementation package (release-candidate work) |
| `release_qa1b/` | qa1b release candidate, incl. clean-room extract |
| `reserved_run_2026-08-15/` | **Kimi reserved run**: 1440/1440 calls, raw + parsed responses, scoring records, freeze records, defect/restart decision logs |
| `patch_qa1c/` | Parser patch for DEFECT_001 (Kimi emits `◁/think` without `▷`; 35 valid answers mis-scored) |
| `release_qa1c/` | Frozen release qa1c (dependency pins, freeze records) |
| `analysis/` | Section-6 analysis scripts and results |
| `bedrock_terra/` | **Terra and Qwen3 arms**: adapters, configs, dev + reserved runs, repeat runs, ablations, effort studies, coverage studies, analyses, HTML reports, authorisation/signature records, pre-registrations |
| `audit_extension/` | **Experiment-1 audit extension**: contracts, schemas, fixtures, deterministic validators, blind validator spec pack, results for dev/reserved splits of all three arms, exploratory reports |

Each subdirectory keeps its own `README.md` / reports where they existed;
internal paths in those documents refer to this same layout.

## Provenance and integrity

- Reserved splits were executed under sealed conditions; scoring and
  analysis were opened only after the corresponding authorisation records
  (see `bedrock_terra/signature/` and the freeze records in each release).
- Run manifests, SHA-256 freeze records and pre-registration hashes are
  included. Note the sanitization below: a few of those files were edited
  *after* freezing to remove private infrastructure identifiers, so their
  bytes no longer match the recorded hashes — see `SANITIZATION.md` for the
  exact file list.
- Findings and defects are reported as found (e.g. `DEFECT_001`,
  `FINDING_002` addendum, `FINDING_003`), including the ones that were our
  own artefacts.
