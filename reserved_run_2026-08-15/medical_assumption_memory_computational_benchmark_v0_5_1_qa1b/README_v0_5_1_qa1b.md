# Cognitive Memory Benchmark v0.5.1-qa1b — release candidate

This package is a clean extraction of the v0.5.1 release with the qa1b corrective overlay
applied, prepared against the *Official Response to the External QA Review* of
14 August 2026.

**The reserved 1,440-call evaluation is NOT authorised and was not touched.** No model
call was issued while preparing this candidate. Every check below is either a non-LLM
design audit, a local fault-injection test, or a mock run.

## What changed relative to v0.5.1

Dataset, oracle, splits, prompts and condition definitions are unchanged and
checksum-verified against the original release archive. Only execution and measurement
logic changed.

| Area | Change |
| --- | --- |
| Final-answer extraction | `scripts/qa_core.py` — Kimi Unicode markers, truncation decided by `finish_reason` or an unclosed reasoning block, drafts inside the reasoning block ignored |
| Runner | `scripts/qa_runner.py` — retry restricted to 429/5xx/timeouts, terminal statuses, restart safety, duplicate-terminal guard, completion validator |
| Adapter | `scripts/adapters/openai_compatible_adapter_qa1.py` — keyless endpoints, `finish_reason` propagation, HTTP error bodies surfaced, `conversation_id` never sent |
| Scorer | `scripts/api_runner_qa1.py` — per-group decisive-evidence hits, all-required-groups coverage, certified meta-decision accuracy |
| Shortcut audit | `scripts/design_audit_qa1b.py` — chance-relative audit over all 40 memories, replacing the retired one-sided eight-memory gate |
| Terminology | `public/terminology_v0_5_1.json`, `config/reporting_config.json` |
| Release integrity | `scripts/verify_manifest.py`, `scripts/build_freeze_record.py` |

`public/world_specification.json` is deliberately left byte-identical to the v0.5.1
release. The paper-aligned condition names live in `public/terminology_v0_5_1.json`
instead, so that dataset and prompt identity stay checksum-verifiable.

## Reproducing the pre-freeze validation

Run in this order. The manifest must be generated last.

```bash
python scripts/validate_v0_5_1.py                     # structural validation
python tests/test_core.py                             # v0.5.1 core tests
python tests/test_pre_llm_qa1b.py                     # qa1b regression suite
python tests/test_production_faults_qa1b.py           # retry / timeout / outage / restart
python tests/test_live_marker_extraction_qa1b.py      # extraction vs real endpoint captures
python scripts/design_audit_qa1b.py                   # 40-memory chance-relative audit (~3 min)
python scripts/api_runner_qa1.py \
    --config config/model_config.example.json \
    --split development --output results/qa1b_mock_dev # end-to-end, mock adapter
python scripts/build_freeze_record.py                 # unsigned freeze record
python scripts/build_manifest.py                      # manifest, LAST operation
python scripts/verify_manifest.py                     # verify every digest
```

## Status under the 15 August release decision

The project decision of 15 August 2026 froze the dataset, oracle, prompts, condition
definitions, cognitive-memory representation, shortcut family, outcome hierarchy, parser
policy, retry policy and estimator. The shortcut audit is frozen as **pass with disclosed
residual current-only signal**. This package implements that decision; no experimental
mechanism was changed.

Configuration aligned to the decision:

- `config/reporting_config.json` now specifies intention-to-evaluate denominators (every
  expected call counted, invalid and truncated output scored incorrect), the hierarchical
  confirmatory sequence, and memory-clustered bootstrap with 10,000 replicates. The earlier
  draft specified exact McNemar and excluded invalid output; both are retired by sections 5
  and 6 of the decision.
- Provenance measures follow section 7: provenance-reference validity and decisive-citation
  validity are supporting, historical hit, current hit and dual-source completeness are
  descriptive. "Certified meta-decision accuracy" is **not** a confirmatory endpoint and is
  no longer reported under that name.
- `validation/DEPRECATION_NOTICE_validate_v0_5_1.md` marks the legacy shortcut output
  non-authoritative while the file itself stays byte-identical.

## One finding that must be recorded in the freeze

**The authoritative shortcut audit is not stable across scikit-learn major versions.**
Running the Annex B interpreter checks surfaced this. With the pinned stack the audit
reproduces identically on CPython 3.8.10 and 3.11.16. Under scikit-learn 1.9.0 the probe
predictions change materially and the verdict flips:

| Stack | current-only transferable | p (Holm) | Audit |
| --- | --- | --- | --- |
| Python 3.8.10 + scikit-learn 1.3.2 | 0.256 | 0.455 | PASS |
| Python 3.11.16 + scikit-learn 1.3.2 | 0.256 | — | PASS (reproduces 3.8) |
| Python 3.11.16 + scikit-learn 1.9.0 | 0.287 | 0.048 | FAIL |

Under the newer stack `template_only` also rises from 0.204 to 0.400 on the same statistic.
The cause is `LogisticRegression` fitting behaviour, not the audit method, and the
interpreter is not implicated. The remedy is administrative: `config/requirements_frozen.txt`
pins the analysis dependencies, and the frozen verdict is valid only under those pins.
Evidence for all three runs is in `validation/interpreter_evidence/`.

## Annex B checklist

All gates are evidenced except the governance signature, which rests with the decision
owner. Run `python scripts/release_checks_qa1b.py` to reproduce items 4 to 7 and
`python scripts/verify_manifest.py` to reproduce item 10.
