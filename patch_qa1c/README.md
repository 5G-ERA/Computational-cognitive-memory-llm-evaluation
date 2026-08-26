# Proposed corrective release v0.5.1-qa1c — DEFECT_001

**Status: PROPOSED, NOT APPLIED.** Nothing in the frozen release has been modified. This
package is a patch, a regression suite and a verification tool, prepared so that the project
decision owner can approve or reject a corrective release without having to build one.

**Authority required:** Official Release and Assessment Decision v0.5.1-qa1b, Annex D — a
corrective release requires a documented rationale, renewed checksums and a new signature
before reserved execution continues.

---

## The defect

Kimi-Dev-72B occasionally emits the reasoning end marker as `◁/think`, dropping the closing
`▷`, and then produces a complete, valid final answer. The frozen parser matches only
`◁/think▷`, so it sees an unclosed reasoning block and applies rule 2 of the frozen extraction
policy: classify as `COMPLETED_OUTPUT_TRUNCATED`. Under intention-to-evaluate that reply is
then scored **incorrect**.

The parser follows the frozen specification exactly. The specification did not anticipate a
malformed end marker.

Full analysis: `../reserved_run_2026-08-15/DEFECT_001_malformed_end_marker.md`.

## The change

One marker added, and a tie-break made explicit. Nothing else.

```
END_MARKERS = (..., "◁/think▷", "◁/think")
```

The tolerant form is listed **after** the well-formed one, and marker selection now takes the
**longest** match at the earliest position, so a well-formed `◁/think▷` is never cut as its
own `◁/think` prefix leaving a stray glyph in the segment.

Unchanged: `finish_reason` remains authoritative for truncation; drafts inside the reasoning
block are still ignored; exactly one final object is still required; a marker-less complete
message is still parsed on its merits. Dataset, oracle, split, prompts, condition definitions,
retry policy, outcome hierarchy and estimator are untouched.

## Contents

| Path | Purpose |
| --- | --- |
| `patch/scripts/qa_core.py` | corrected parser |
| `patch/config/extraction_policy.json` | marker list updated to match |
| `tests/test_qa1c_marker_tolerance.py` | 16 checks: what the fix recovers, and what it must not change |
| `tools/parser_diff_report.py` | differential verification against the frozen parser, offline |

## Verification already performed

Regression suite: **16/16 pass**, including the three that matter most — genuine
`finish_reason == 'length'` truncation stays truncated, `length` wins even when a marker is
recovered, and an unclosed block with no end marker at all stays truncated.

Differential verification against **1,260 collected reserved responses**, run offline with no
model call:

| | Before | After |
| --- | --- | --- |
| `COMPLETED_VALID` | 1,175 | 1,207 |
| `COMPLETED_OUTPUT_TRUNCATED` | 85 | 53 |
| Records changed | | **32** |

- **Check 1 — every change is truncated → scorable: PASS.** No record moved in any other
  direction.
- **Check 2 — no genuinely truncated record becomes scorable: PASS.** Zero wrongly rescued.
- **Check 3 — truncation by condition:**

| Condition | Before | After |
| --- | --- | --- |
| B0_LLM_ALONE | 7.58% | 3.79% |
| B1_VERIFIED_MEMORY | 5.33% | 3.39% |
| M0_OPEN_LOOP_MEMORY | 7.29% | 5.41% |
| **Pooled** | **6.75%** | **4.21%** |

Between-arm spread after correction: 2.02%, within the section 5 `ok` band.

**Condition accuracy was not computed at any point.** The correction is judged on extraction
behaviour alone, before any outcome is inspected. That discipline must hold until the
corrective release is signed.

## To apply, after approval

```bash
python tools/parser_diff_report.py \
    --raw  <run>/results/reserved_2026-08-15/responses_raw.jsonl \
    --scoring <run>/results/reserved_2026-08-15/scoring_records.jsonl
python tests/test_qa1c_marker_tolerance.py
# then copy patch/ over the package, regenerate the manifest LAST, re-sign,
# and re-score the complete reserved set from responses_raw.jsonl
```

Re-scoring consumes **no model calls**: every response is preserved verbatim.

## To disclose in the write-up

The malformed-marker rate is a property of the served model build and belongs in the results
as observed model behaviour, not hidden in a patch note. Observed at 32 of 1,260 responses
(2.5%) during reserved execution.
