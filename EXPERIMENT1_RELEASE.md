# Experiment 1 release mapping — Supplementary Note 7 (V5.8)

This document maps the contents of this repository onto **Supplementary
Note 7 (LLM Multi-Model Evaluation)** of *A Computational Theory of
Cognitive Memory* (draft V5.8, 2026-08) and populates the Note's
`[TO COMPLETE]` fields from the frozen execution records stored here.
Every number below is read from a file in this repository; paths are
given so the extraction can be reproduced.

## Condition and contrast terminology

| Paper (V5.8) | Benchmark condition id |
|---|---|
| Raw longitudinal evidence | `B0_LLM_ALONE` |
| Pre-specified consequence map | `M0_OPEN_LOOP_MEMORY` |
| Cognitive-memory representation | `B1_VERIFIED_MEMORY` |

Contrasts: Δ_CM−Raw = B1−B0 (primary), Δ_CM−Map = B1−M0 (key
secondary), Δ_Map−Raw = M0−B0 (exploratory). Percentile bootstrap,
10,000 replicates, clustered at the memory-group level,
intention-to-evaluate denominator.

## §7.3 — Experimental unit, matching and data partition

- Independent memory groups: **32** (reserved split); **8** (development split).
- Matched decision contexts: **480** reserved; **120** development.
- Expected calls per model: **1440** reserved (480 per condition);
  **360** development. Every expected call has one terminal record
  (`run_completion_report.json` in each run directory).
- Benchmark and split: v0.5.1 family; frozen release **qa1c**
  (`release_qa1c/…/validation/freeze_record_v0_5_1_qa1c.json`, which
  also pins qa1b provenance and dependency versions).
- Identifiers: `memory_id`, `context_id`, `canonical_id` and rendering
  suffix in every scoring record (e.g.
  `audit_extension/results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl`).

## §7.4 — Table 2: model-specific execution manifest

Read from `…/reserved_*/run_manifest.json` of each arm.

| Field | paper "GPT-4.6 Terra" | paper "KIMI2" | Qwen3 |
|---|---|---|---|
| Provider/endpoint | Amazon Bedrock, OpenAI-compatible runtime, us-east-1, global CRIS routing | Private OpenAI-compatible endpoint (hostname redacted, see `SANITIZATION.md`) | Amazon Bedrock, OpenAI-compatible runtime, us-east-1, global CRIS routing |
| Endpoint verified | 2026-08-19 | 2026-08-14 | 2026-08-19 |
| Model/checkpoint identifier | `global.openai.gpt-5.6-terra` | `kimi-dev-72b` — snapshot `moonshotai_Kimi-Dev-72B-Q4_0.gguf` | `qwen.qwen3-next-80b-a3b` |
| Quantisation | Not disclosed (managed service; `model_snapshot: NOT_AVAILABLE`) | Q4_0 (GGUF) | Not disclosed (managed service) |
| Temperature/sampling | Sampling params not sent (`send_sampling_params: false`); `reasoning_effort: low` | temperature 0, top_p 1, seed 13082642 | Sampling params not sent; `reasoning_effort: low` |
| Output budget | 4096 (`max_completion_tokens`), client-side hard cost cap | 4096 | 4096 (`max_completion_tokens`), client-side hard cost cap |
| Prompt version | benchmark 0.5.1-qa1b (frozen) | benchmark 0.5.1-qa1b (frozen) | benchmark 0.5.1-qa1b (frozen) |
| Parser/scorer version | qa1c (frozen parser, DEFECT_001 fix; `patch_qa1c/`) | qa1c | qa1c |
| Configuration hash | `bedrock_terra/RECORD_SHA256.txt` | freeze records in `release_qa1c/…/validation/` | `bedrock_terra/RECORD_SHA256.txt` |
| Run manifest | `bedrock_terra/out/reserved_terra/run_manifest.json` | `reserved_run_2026-08-15/…/results/reserved_2026-08-15/run_manifest.json` | `bedrock_terra/out/reserved_qwen3/run_manifest.json` |

> ⚠ **Label reconciliation needed before submission.** The paper labels
> the second arm "KIMI2", but the executed checkpoint recorded in the
> frozen manifest is `kimi-dev-72b`
> (`moonshotai_Kimi-Dev-72B-Q4_0.gguf`). These are different models of
> the Kimi family. Either the paper label or the manifest citation must
> be corrected; the executed checkpoint is authoritative for what was run.

## §7.7 — Table 3: multi-model outcomes (reserved split)

Accuracies are intention-to-evaluate over 480 calls per condition.
Sources: `bedrock_terra/out/analysis_reserved_terra.json`,
`bedrock_terra/out/analysis_reserved_qwen3.json`, and (for the Kimi arm)
recomputation from
`audit_extension/results/kimi_confirmatory/kimi_reserved_scored_qa1c.jsonl`,
which reproduces the signed confirmatory result exactly.

| Model (paper label) | Raw (B0) | Map (M0) | CM (B1) | Δ_CM−Raw pp [95% CI] | Δ_CM−Map pp [95% CI] | Δ_Map−Raw pp [95% CI] | Confirmatory status |
|---|---|---|---|---|---|---|---|
| GPT-4.6 Terra | 96.67% | 95.21% | 97.71% | +1.04 [−0.63, +2.92] | not tested (gated on primary) | −1.46 [−2.92, −0.21] (exploratory) | NOT ESTABLISHED — ceiling effect |
| KIMI2 (`kimi-dev-72b`) | 74.17% | 70.42% | 83.96% | **+9.79 [+5.00, +14.79]** | +13.54 | includes zero | **POSITIVE** (sealed run, signed) |
| Qwen3 | 29.38% | 25.42% | 54.58% | **+25.21 [+21.67, +28.54]** | +29.17 [+25.42, +32.92] | −3.96 [−7.08, −0.83] | **POSITIVE** (pre-registered replication) |

Family-level (secondary, pre-registered:
`bedrock_terra/exp/PREREG_family_pattern_2026-08-20.md`, SHA-256
`f657099571…`): Δ_CM−Raw in the TEMPORAL_GAP family is **+7.29 pp
(Terra)**, +28.12 pp (Kimi arm), +29.17 pp (Qwen3) — the source of the
main paper's "GPT-4.6 improved by 7.29 points in the temporal-gap
family". Full per-family table: `bedrock_terra/exp/exp1_family_pattern.json`
and `bedrock_terra/EDCA_instrument_studies_2026-08-20.html`.

Declared caveats: with 32 clusters the bootstrap undercovers (~92.5% vs
nominal 95%, disclosed at freeze); Qwen3 under B0 collapses to
`ESCALATE_REVIEW` (~89%), so its benefit concentrates in non-escalate
items; Terra's null is an instrument ceiling, not evidence against the
mechanism.

Machine-readable version: [`results_table_v5_8.json`](results_table_v5_8.json).

## §7.9 — Reproducibility checklist mapping

| Checklist item | Where in this repository |
|---|---|
| Benchmark and split hashes | `release_qa1c/…/validation/freeze_record_v0_5_1_qa1c.json`; `bedrock_terra/RECORD_SHA256.txt` |
| Source and rendered condition files | benchmark packages (`release_qa1c/`, mirrored in `reserved_run_2026-08-15/`) |
| Prompt templates | benchmark packages, frozen at 0.5.1-qa1b |
| Model-specific execution manifests | the three `run_manifest.json` files listed above |
| Raw terminal captures | `reserved_run_2026-08-15/…/results/reserved_2026-08-15/responses_raw.jsonl`; `bedrock_terra/out/reserved_*/` |
| Parser and scorer versions | `patch_qa1c/` (DEFECT_001 fix and tests) |
| Terminal-record audit | `run_completion_report.json` per run; `attempts.jsonl`, `call_registry.jsonl` |
| Analysis scripts | `bedrock_terra/analysis_dev_arm.py`, `bedrock_terra/exp/`, `analysis/` |
| Bootstrap seed and population hashes | run manifests and analysis outputs (`analysis_reserved_*.json`); prereg SHA-256 files in `bedrock_terra/exp/` |
| Machine-readable results table | `results_table_v5_8.json` |
| One-command verification | `reproduce/verify_experiment1.py` (offline re-derivation of all three arms, incl. bootstrap intervals) |

Rescoring uses preserved captures only; no additional model calls are
required or permitted. See `REPRODUCIBILITY.md` for the pipeline map,
seeds, seals and the scoring rule.

## Open items before submission

1. **KIMI2 vs `kimi-dev-72b`** label reconciliation (above).
2. A pre-registered replay-recall confirmatory test on the untouched
   Kimi arm exists (`audit_extension/validation/PREREG_replay_recall_kimi_2026-08-22.json`)
   and **has not been executed**; it must not be reported as a result.
3. Private infrastructure identifiers were redacted after freeze in 28
   files (`SANITIZATION.md`); byte-level hashes of those specific files
   no longer match the freeze records. All scientific content is intact.
4. The audit-extension findings (`audit_extension/`) are exploratory as
   declared in their reports and are not part of the Note 7 endpoints.
