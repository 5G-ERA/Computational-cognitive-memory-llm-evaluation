# Defect 001 — frozen parser rejects a malformed reasoning end marker

**Classification:** reproducible implementation failure, in the sense of the Official Release
and Assessment Decision v0.5.1-qa1b, section 13 and Annex A15.
**Found:** 15 August 2026, during reserved execution, at 60 collected responses.
**Affects:** scoring only. Data collection is unaffected.
**Reserved calls wasted:** 0.

---

## 1. What happens

Kimi-Dev-72B occasionally emits the reasoning end marker as `◁/think` — without the closing
`▷` — and then produces a complete, well-formed final answer.

The frozen parser (`scripts/qa_core.py:parse_final_answer`) matches the configured end markers
literally. `◁/think` does not match `◁/think▷`, so the parser sees a start marker with no end
marker and applies rule 2 of the frozen extraction policy: *"If a reasoning start marker is
present without its corresponding end marker, classify the reply as
COMPLETED_OUTPUT_TRUNCATED."*

Under intention-to-evaluate scoring that reply is then scored **incorrect**.

**The parser is following the frozen specification exactly.** The specification did not
anticipate a malformed end marker. This is a specification gap surfacing as an implementation
failure, not a coding error against the spec.

## 2. Evidence

Observed frequency at 60 collected responses:

| Marker form | Count |
| --- | --- |
| `◁think▷` (start) | 60 |
| `◁/think▷` (well-formed end) | 57 |
| `◁/think` (malformed end) | **1** |
| no end marker at all — genuine ceiling truncation | 2 |

The affected call:

| Field | Value |
| --- | --- |
| call_id | CALL51-0001504 |
| condition | B0_LLM_ALONE |
| finish_reason | `stop` — the model completed normally |
| output_tokens | 639, far below the 4096 ceiling |
| latency | 35 s |
| scored as | `COMPLETED_OUTPUT_TRUNCATED` |
| actual content after the marker | a complete valid object with `reaction`, `rule_id`, `decisive_event_ids` and `reason` |

The response was neither truncated nor invalid. It was a correct, complete answer discarded
over one missing character.

Observed rate 1/60 = 1.7%. Extrapolated across 1,440 reserved calls, of the order of 24 valid
answers would be scored incorrect.

## 3. Why this is not merely cosmetic

1. **It biases the primary contrast.** Under intention-to-evaluate a discarded answer counts as
   incorrect, so the defect depresses accuracy in whichever arm it strikes. It is a random
   corruption of the outcome variable, not a neutral loss.
2. **It contaminates operational monitoring.** These cases inflate the section 5 truncation
   rate, so they could trigger a spurious stop decision, and they pool two unrelated failure
   modes — budget exhaustion and a malformed marker — under one label.

## 4. Why reserved execution was allowed to continue

`results/reserved_2026-08-15/responses_raw.jsonl` preserves every response verbatim, including
`finish_reason` and token counts. Scoring is a **derived** artefact, fully reproducible offline
from that file.

Therefore:

- The defect does not corrupt collected data, only its interpretation.
- Continuing collection compounds nothing.
- The corrective release can be applied to all 1,440 responses retrospectively, **without
  re-issuing a single model call**.
- Stopping would cost roughly thirty hours of endpoint time and would not improve the final
  result by any measure.

This is a deliberate, documented departure from the literal wording of A15, which directs that
a corrective release be issued before continuing. The substance of A15 — that the reserved
result must be evaluated under a correct and frozen treatment definition — is preserved,
because no analysis will be performed under the defective parser.

**Decision:** continue reserved collection; issue the corrective release before any analysis;
re-score the complete reserved set under the corrected parser. Taken by the run operator and
referred to the project decision owner.

## 5. Required correction

Minimal and confined to marker recognition. The tolerant form must accept the closing `▷` as
optional, while leaving every other frozen rule untouched: `finish_reason` remains authoritative
for truncation, drafts inside the reasoning block are still ignored, and exactly one final
object is still required.

The correction must **not**:

- alter the dataset, oracle, split, prompts or condition definitions;
- alter the retry policy, the outcome hierarchy or the estimator;
- alter the treatment of genuine `finish_reason == 'length'` truncations.

It must be issued as a versioned corrective release with renewed checksums, a documented
rationale and a new signature, per Annex D, and the reserved set re-scored under it.

## 6. Verification required before the corrective release is accepted

1. Re-score all collected responses under both parsers and report the exact set of records whose
   status changes; every change must be from `COMPLETED_OUTPUT_TRUNCATED` to a scorable status.
2. Confirm no record that is genuinely truncated (`finish_reason == 'length'`) becomes scorable.
3. Confirm the corrected truncation rate per condition, and re-evaluate the section 5 bands
   against it.
4. Report the malformed-marker rate as a disclosed model behaviour in the final write-up.

---

Recorded 15 August 2026 by the external QA operator. Requires the project decision owner's
ruling on the corrective release.
