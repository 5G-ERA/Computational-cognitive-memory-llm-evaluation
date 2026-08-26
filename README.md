# Computational Cognitive Memory — LLM Evaluation

Results and reproducibility package for **Experiment 1 (LLM Multi-Model
Evaluation)** of *A Computational Theory of Cognitive Memory* (Qiu,
Pham, Lendinez Ibanez, Li — University of Bedfordshire / University of
Birmingham, draft V5.8, 2026-08). The paper introduces **Computational
Cognitive Memory (CCM)**: a DCA-scoped cognitive interface plus
governed cognitive dynamics realised through Distributed Cognitive
Continuity (DCC). Experiment 1 tests whether an evidence-resolved
cognitive-memory representation improves an LLM's meta-decision over
raw longitudinal evidence and over a pre-specified consequence map
built from the same source material. (Experiment 2, the robotic
evaluation, is not in this repository.)

## Results

Reserved (confirmatory) split: 32 memory groups, 480 matched contexts,
1440 calls per model, intention-to-evaluate, percentile bootstrap with
10,000 replicates clustered at the memory-group level. Conditions:
**Raw** = `B0_LLM_ALONE`, **Map** = `M0_OPEN_LOOP_MEMORY`,
**CM** = `B1_VERIFIED_MEMORY`. Primary contrast **Δ = CM − Raw**.

| Arm (paper label) | Executed model | Raw | Map | CM | Δ CM−Raw (pp) | 95% CI | Status |
|---|---|---|---|---|---|---|---|
| KIMI2 † | `kimi-dev-72b` (Q4_0) | 74.17% | 70.42% | 83.96% | **+9.79** | [+5.00, +14.79] | POSITIVE — sealed run, signed |
| Qwen3 | `qwen.qwen3-next-80b-a3b` | 29.38% | 25.42% | 54.58% | **+25.21** | [+21.67, +28.54] | POSITIVE — pre-registered replication |
| GPT-4.6 Terra | `global.openai.gpt-5.6-terra` | 96.67% | 95.21% | 97.71% | +1.04 | [−0.63, +2.92] | NOT ESTABLISHED — instrument ceiling |

Key secondary (CM − Map, gated on the primary): +13.54 pp (Kimi arm),
+29.17 pp [+25.42, +32.92] (Qwen3) — the benefit requires resolving
what the evidence supported, not merely exposing the expected
consequence relation, whose effect is null or negative (Map − Raw:
−3.96 pp [−7.08, −0.83] in Qwen3, exploratory).

Pre-registered family analysis (secondary): the largest effect
concentrates in the **TEMPORAL_GAP** family — +28.12 pp (Kimi arm),
+29.17 pp (Qwen3), and **+7.29 pp for Terra**, whose only margin below
ceiling is exactly there
(`bedrock_terra/exp/exp1_family_pattern.json`).

Machine-readable: [`results_table_v5_8.json`](results_table_v5_8.json).
Paper mapping (Supplementary Note 7 manifest and results tables):
[`EXPERIMENT1_RELEASE.md`](EXPERIMENT1_RELEASE.md).

† The paper label and the executed checkpoint differ; see the
reconciliation note in `EXPERIMENT1_RELEASE.md`.

**Declared caveats.** Qwen3 under Raw collapses to `ESCALATE_REVIEW`
(~89%), so its benefit concentrates in non-escalate items. Terra's
null is a ceiling of the instrument, not evidence against the
mechanism. With 32 clusters the bootstrap undercovers (~92.5% vs
nominal 95%), disclosed at freeze. The audit-extension findings
(`audit_extension/`) are exploratory; a pre-registered replay-recall
test on the untouched Kimi arm has **not been executed**.

## Reproduce the results

Offline, from the frozen records in this repository — no model calls.
Requires Python ≥ 3.8 and numpy.

```bash
python3 reproduce/verify_experiment1.py
```

This re-derives the Terra and Qwen3 reserved results from the raw
terminal captures through the frozen pipeline (parse → scoring →
frozen clustered bootstrap, deterministic seed) and checks accuracies,
contrasts **and intervals** against the frozen outputs; the Kimi arm is
recomputed from the qa1c-scored records of its sealed confirmatory run.
Expected final line: `All three arms reproduce the frozen results…`.

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) for the pipeline map,
seeds, seals and authorisation records, the scoring rule (and a trap to
avoid), integrity hashes, and exactly what cannot be reproduced from
here.

## Repository layout

Ordered by function; internal paths in the frozen reports refer to this
same layout, so directories are not renamed.

**Results and analysis**

| Path | Content |
|---|---|
| `results_table_v5_8.json` | Machine-readable multi-model outcomes |
| `bedrock_terra/out/analysis_reserved_*.json` | Frozen confirmatory analyses (Terra, Qwen3) |
| `audit_extension/results/kimi_confirmatory/` | qa1c-scored records of the sealed Kimi-arm run |
| `bedrock_terra/exp/` | Pre-registered family/repeat analyses + SHA-256 preregs |
| `analysis/` | Signed frozen estimator (`analysis_section6.py`) and section-6 outputs |
| `bedrock_terra/EDCA_*.html` | Execution, eligibility, results and instrument reports |

**Reproduction**

| Path | Content |
|---|---|
| `reproduce/verify_experiment1.py` | One-command offline verification of all three arms |
| `reproduce/run_frozen_analysis.py` | Runs the frozen pipeline on a preserved run directory |
| `bedrock_terra/analysis_dev_arm.py` | Frozen analysis entry point (seal-enforcing) |
| `bedrock_terra/signature/` | Signed authorisation/inspection records that release the seals |

**Frozen benchmark and execution records**

| Path | Content |
|---|---|
| `release_qa1c/` | Frozen benchmark release qa1c (prompts, oracle, freeze records, pins) |
| `reserved_run_2026-08-15/` | Kimi-arm reserved run: 1440/1440 raw captures, manifests, defect logs |
| `bedrock_terra/out/reserved_*/` | Terra and Qwen3 reserved runs: raw captures, manifests, completion reports |
| `bedrock_terra/config/`, `bedrock_terra/adapters/` | Frozen model configs and transport adapters |

**History and QA (how the release got here)**

| Path | Content |
|---|---|
| `medical_assumption_memory_computational_benchmark_v0_5_1/` | Benchmark v0.5.1 as received |
| `medical_assumption_memory_v0_5_1_qa1_patch/`, `pkg_qa1b/`, `release_qa1b/` | qa1 review and qa1b release-candidate work |
| `patch_qa1c/` | Parser fix for DEFECT_001 (35 valid answers mis-scored) |
| `audit_extension/` | Experiment-1 audit extension: contracts, validators, exploratory results |

## Provenance and integrity

- Reserved splits were executed sealed; scoring and analysis opened
  only under the signed authorisation records in
  `bedrock_terra/signature/` — the analysis tooling refuses to run
  without them, by code.
- Run manifests, SHA-256 freeze records, prereg hashes and dependency
  pins are included. 28 files had private infrastructure identifiers
  redacted *after* freeze for publication (`SANITIZATION.md`), so the
  bytes of those specific files no longer match the recorded hashes.
- Defects found along the way are reported as found (`DEFECT_001`,
  `FINDING_002` addendum, `FINDING_003`), including the ones that were
  our own artefacts.
